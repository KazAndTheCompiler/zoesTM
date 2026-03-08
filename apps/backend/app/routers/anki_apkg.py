"""
APKG-like export/import endpoints for zoesTM Anki integration.
Current implementation is experimental (zip+csv layout), not full Anki-compatible APKG fidelity.
"""
# Endpoints map:
# Owner: anki-apkg
# POST /anki-apkg/decks/{deck_id}/export-apkg
# GET /anki-apkg/decks/{deck_id}/apkg
# POST /anki-apkg/import-apkg
# GET /anki-apkg/deck-names
import csv
import io
import json
import uuid
import zipfile
from datetime import UTC, datetime
from fastapi import APIRouter, UploadFile, File
from ..repositories import review_repo
from ..services import events
from ..errors import ApiError, bad_request, not_found

router = APIRouter()


def create_apkg(deck_id: str) -> tuple[str, bytes]:
    """
    Create a .apkg file containing all cards from the deck.
    Returns:
        (filename, zip_bytes)
    """
    cards = review_repo.get_all_cards_for_export(deck_id)
    if not cards:
        raise not_found('deck_empty', 'No cards in deck', {'deck_id': deck_id})

    deck = review_repo.get_deck(deck_id)
    deck_name = deck.get('name', 'deck')

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # collection.conf
        zip_file.writestr('collection.anki2/collection.conf', json.dumps({
            'creator': 'zoesTM',
            'curDecks': {'1': {'name': deck_name}},
            'mod': int(datetime.now(UTC).timestamp()),
            'nextID': 100000000,
            'sortFieldName': 'noteField1',
            'sortOrder': 0,
            'srcRevNumber': 1,
            'usn': 0,
            'yaml': f'deckOrder: 1\ngid: {uuid.uuid4()}',
        }, indent=2))

        # notes1.csv
        notes_csv = io.StringIO()
        notes_writer = csv.writer(notes_csv)
        notes_writer.writerow([
            'id', 'guid', 'mid', 'nfd', 'usn', 'mod', 'tag', 'flds',
            'sfld', 'csum', 'flags', 'data', 'dupe', 'model'
        ])
        for i, card in enumerate(cards):
            notes_writer.writerow([
                i + 1,
                str(uuid.uuid4()),
                1, 0, 0,
                int(datetime.now(UTC).timestamp()),
                '|'.join(card.get('tags', [])),
                f"{card.get('front', '')}|||{card.get('back', '')}",
                card.get('front', ''),
                0, 0, '', 0, 1,
            ])
        zip_file.writestr('collection.anki2/notes1.csv', notes_csv.getvalue())

        # models1.json
        zip_file.writestr('collection.anki2/models1.json', json.dumps([{
            'id': 1,
            'name': 'zoesTM card',
            'flds': [
                {'name': 'Front', 'ord': 0, 'sticky': False, 'rtl': False, 'font': 'Arial,11px'},
                {'name': 'Back', 'ord': 1, 'sticky': False, 'rtl': False, 'font': 'Arial,11px'},
            ],
            'css': 'card { font-family: Arial; font-size: 11px; }',
            'tmpls': [{
                'name': 'Card 1',
                'ord': 0,
                'qfmt': '{{Front}}',
                'afmt': '{{FrontSide}}<hr>{{Back}}',
                'did': 1,
            }],
            'cat': 'zoesTM',
        }]))

        # cards.csv
        cards_csv = io.StringIO()
        cards_writer = csv.writer(cards_csv)
        cards_writer.writerow([
            'nid', 'ord', 'did', 'mod', 'usn', 'due', 'odue', 'type', 'queue',
            'ivl', 'left', 'odid', 'flags', 'data'
        ])
        for i, card in enumerate(cards):
            # Parse next_review_at to epoch seconds; default to now
            nxt = card.get('next_review_at')
            try:
                if nxt:
                    dt = datetime.fromisoformat(nxt.replace('Z', '+00:00'))
                    due = int(dt.timestamp())
                else:
                    due = int(datetime.now(UTC).timestamp())
            except Exception:
                due = int(datetime.now(UTC).timestamp())

            ivl = card.get('last_interval_days') or 1
            cards_writer.writerow([
                i + 1,  # nid
                0,      # ord
                1,      # did (deck id in Anki)
                int(datetime.now(UTC).timestamp()),  # mod
                0,      # usn
                due,    # due (epoch seconds)
                0,      # odue
                1,      # type (0=new, 1=learning, 2=review; we map new to 0? but simple)
                0,      # queue
                int(ivl),  # ivl (interval days)
                0,      # left (reps left)
                0,      # odid
                0,      # flags
                '',     # data
            ])
        zip_file.writestr('collection.anki2/cards.csv', cards_csv.getvalue())

    zip_buffer.seek(0)
    filename = f"{deck_id}.apkg"
    return filename, zip_buffer.getvalue()


@router.post('/decks/{deck_id}/export-apkg')
def export_apkg(deck_id: str):
    """
    Export a deck as a .apkg file (Anki package).
    Returns JSON with base64 data.
    """
    deck = review_repo.get_deck(deck_id)
    if not deck:
        raise not_found('deck_not_found', 'Deck not found', {'deck_id': deck_id})

    filename, zip_bytes = create_apkg(deck_id)

    events.emit_event('anki_export', {
        'deck_id': deck_id,
        'deck_name': deck.get('name'),
        'card_count': len(review_repo.get_all_cards_for_export(deck_id)),
    }, idempotency_key=f'export_apkg:{deck_id}')

    import base64
    return {
        'filename': filename,
        'content_type': 'application/zip',
        'encoding': 'base64',
        'size': len(zip_bytes),
        'data': base64.b64encode(zip_bytes).decode('utf-8'),
    }


@router.get('/decks/{deck_id}/apkg')
async def download_apkg(deck_id: str, callback_url: str | None = None):
    """
    Download a deck as .apkg file.
    """
    deck = review_repo.get_deck(deck_id)
    if not deck:
        raise not_found('deck_not_found', 'Deck not found', {'deck_id': deck_id})

    filename, zip_bytes = create_apkg(deck_id)

    events.emit_event('anki_download', {
        'deck_id': deck_id,
        'deck_name': deck.get('name'),
        'source': 'api_download',
    })

    if callback_url:
        import httpx
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(callback_url, json={
                    'deck_id': deck_id,
                    'success': True,
                    'filename': filename,
                })
        except Exception as e:
            import logging
            logging.warning(f"APKG callback failed: {e}")

    from fastapi.responses import Response
    return Response(
        content=zip_bytes,
        media_type='application/zip',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )


@router.post('/import-apkg')
async def import_apkg(file: UploadFile = File(...), fmt: str = 'apkg', target_deck_name: str | None = None):
    """
    Import a .apkg file and create cards.
    Args:
        file: raw .apkg file content
        fmt: file format ('apkg' expected)
        target_deck_name: optional deck name to add to (creates if not exists)
    Returns:
        JSON with import results
    """
    if fmt != 'apkg':
        raise bad_request('invalid_format', 'Only .apkg format is supported')

    content = await file.read()
    zip_buffer = io.BytesIO(content)
    deck_name = target_deck_name or f"imported_deck_{uuid.uuid4().hex[:8]}"

    try:
        with zipfile.ZipFile(zip_buffer, 'r') as z:
            # Extract notes CSV
            try:
                notes_bytes = z.read('collection.anki2/notes1.csv')
            except KeyError:
                raise bad_request('import_failed', 'APKG missing notes1.csv')

            notes_csv = notes_bytes.decode('utf-8') if isinstance(notes_bytes, bytes) else notes_bytes
            notes = list(csv.DictReader(notes_csv.splitlines()))

            # Determine deck name from collection.conf if present
            try:
                conf_bytes = z.read('collection.anki2/collection.conf')
                conf_str = conf_bytes.decode('utf-8') if isinstance(conf_bytes, bytes) else conf_bytes
                conf = json.loads(conf_str)
                decks = conf.get('curDecks', {})
                if decks:
                    # Take the first deck name from the conf if not provided
                    first_deck = next(iter(decks.values()))
                    inferred_name = first_deck.get('name')
                    if inferred_name:
                        deck_name = inferred_name
            except Exception:
                pass

            # Create deck
            existing = review_repo.get_deck_by_name(deck_name)
            if existing:
                deck_id = existing['id']
            else:
                deck_id = review_repo.create_deck(deck_name)['id']

            # Import cards
            created = 0
            for note in notes:
                front = note.get('sfld', '').strip()
                back = note.get('flds', '').strip()
                if not front or not back:
                    continue
                tags_str = note.get('tag', '')
                tags = [t.strip() for t in tags_str.split('|') if t.strip()]

                review_repo.create_card(
                    deck_id=deck_id,
                    front=front,
                    back=back,
                    source='import_apkg',
                    tags=tags,
                )
                created += 1

            events.emit_event('anki_import', {
                'deck_id': deck_id,
                'deck_name': deck_name,
                'card_count': created,
            })

            return {
                'success': True,
                'deck_id': deck_id,
                'deck_name': deck_name,
                'cards_created': created,
            }

    except ApiError:
        raise
    except Exception as e:
        import logging
        logging.exception("APKG import failed")
        raise bad_request('import_failed', 'Failed to parse APKG file', {'error': str(e)})


@router.get('/deck-names')
def list_deck_names():
    """Get a simple list of deck names for UI selection."""
    return {'decks': [d.get('name') for d in review_repo.list_decks()]}
