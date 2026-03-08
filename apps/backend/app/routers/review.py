from datetime import UTC, datetime, timedelta
from fastapi import APIRouter, UploadFile, File, Body, Query
from ..services.spaced import compute_next_interval
from ..repositories import review_repo
from ..errors import bad_request, not_found
from ..services import events

router = APIRouter()


@router.post('/decks')
def create_deck(name: str):
    try:
        deck = review_repo.create_deck(name)
        events.emit_event('review.deck_created', {'deck_id': deck['id'], 'name': deck['name']})
        return deck
    except ValueError as exc:
        raise bad_request('invalid_deck_name', str(exc))
    except LookupError as exc:
        raise bad_request('duplicate_deck_name', str(exc))


@router.get('/decks')
def decks():
    return {'items': review_repo.list_decks()}


@router.post('/decks/{deck_id}/cards')
def add_card(deck_id: str, front: str, back: str, tags: str = '', source: str = 'manual'):
    if not review_repo.get_deck(deck_id):
        raise not_found('deck_not_found', 'Deck not found', {'deck_id': deck_id})
    tag_list = [x.strip() for x in tags.split('|') if x.strip()]
    return review_repo.create_card(deck_id, front=front, back=back, tags=tag_list, source=source)


@router.post('/rate')
def rate(state: str = 'new', rating: str = 'good', interval: int = 1, ease_factor: float = 2.5):
    result = compute_next_interval(state, rating, interval, ease_factor, reviews_done=0)
    return {'next_state': result['new_state'], 'next_interval_days': result['new_interval'], 'next_ease_factor': result['new_ease_factor']}


@router.get('/session')
def session_state(limit: int = 20, deck_id: str | None = None):
    queue = review_repo.due_cards(limit, deck_id=deck_id)
    if queue:
        top = queue[0]
        return {
            'state': top['state'],
            'interval': top.get('last_interval_days') or 1,
            'last_rating': top.get('last_rating'),
            'card': {'id': top['id'], 'front': top.get('front'), 'back': top.get('back'), 'tags': top.get('tags', [])},
            'queue_size': len(queue),
        }
    return {'queue_size': 0}


@router.post('/session/start')
def start_session(limit: int = 20, deck_id: str | None = None):
    queue = review_repo.due_cards(limit, deck_id=deck_id)
    return {
        'count': len(queue),
        'cards': [
            {
                'id': c['id'],
                'deck_id': c['deck_id'],
                'front': c.get('front'),
                'state': c['state'],
                'next_review_at': c.get('next_review_at'),
                'tags': c.get('tags', []),
            }
            for c in queue
        ],
    }


@router.post('/answer')
def answer(rating: str, card_id: str):
    if not card_id:
        raise bad_request('missing_card_id', 'card_id is required to submit a review answer')
    card = review_repo.get_card(card_id)
    if not card:
        raise not_found('card_not_found', 'Card not found', {'card_id': card_id})
    updated = review_repo.apply_rating(card_id, rating)
    return {
        'session': {
            'state': updated['state'],
            'interval': updated.get('last_interval_days') or 1,
            'last_rating': rating,
        },
        'card': updated
    }


from pydantic import BaseModel

class ImportBody(BaseModel):
    content: str

@router.post('/import')
def import_notes(
    deck_id: str,
    body: ImportBody | None = Body(None),
    fmt: str = 'csv',
    content: str | None = Query(None),
):
    if fmt not in ('csv', 'tsv'):
        raise bad_request('invalid_import_format', 'fmt must be csv or tsv')
    if not review_repo.get_deck(deck_id):
        raise not_found('deck_not_found', 'Deck not found', {'deck_id': deck_id})
    source_text = body.content if body is not None else (content or '')
    return review_repo.import_notes(deck_id, source_text, fmt)


@router.get('/export-preview')
def export_preview(deck_id: str, limit: int = 50):
    if not review_repo.get_deck(deck_id):
        raise not_found('deck_not_found', 'Deck not found', {'deck_id': deck_id})
    return review_repo.export_preview(deck_id, limit)


@router.post('/cards/{card_id}/bury-today')
def bury_today(card_id: str):
    card = review_repo.get_card(card_id)
    if not card:
        raise not_found('card_not_found', 'Card not found', {'card_id': card_id})
    until = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    review_repo.set_card_flags(card_id, bury_until=until)
    return {'card_id': card_id, 'status': 'buried', 'buried_until': until}


@router.post('/cards/{card_id}/suspend')
def suspend(card_id: str):
    card = review_repo.get_card(card_id)
    if not card:
        raise not_found('card_not_found', 'Card not found', {'card_id': card_id})
    review_repo.set_card_flags(card_id, suspend=True)
    return {'card_id': card_id, 'status': 'suspended'}


@router.post('/cards/{card_id}/unsuspend')
def unsuspend(card_id: str):
    card = review_repo.get_card(card_id)
    if not card:
        raise not_found('card_not_found', 'Card not found', {'card_id': card_id})
    review_repo.set_card_flags(card_id, suspend=False)
    return {'card_id': card_id, 'status': 'active'}


# Endpoints map:
# Owner: review-domain
# POST /review/decks?name=...
# GET /review/decks
# POST /review/decks/{deck_id}/cards?front=...&back=...&tags=t1|t2&source=manual
# POST /review/rate?state=new&rating=good&interval=1
# GET /review/session?limit=20
# POST /review/session/start?limit=20
# POST /review/answer?rating=again|hard|good|easy&card_id=...
# POST /review/import?deck_id=...&fmt=csv|tsv
# GET /review/export-preview?deck_id=...&limit=50
# POST /review/cards/{card_id}/bury-today
# POST /review/cards/{card_id}/suspend
# POST /review/cards/{card_id}/unsuspend


@router.post('/import-apkg')
async def import_apkg(deck_id: str, file: UploadFile = File(...)):
    """Import an Anki .apkg file into a deck. Handles cloze deletions and HTML."""
    if not review_repo.get_deck(deck_id):
        raise not_found('deck_not_found', 'Deck not found', {'deck_id': deck_id})
    import zipfile, tempfile, sqlite3, re, os

    def strip_html(text: str) -> str:
        text = (text.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
                    .replace('&nbsp;', ' ').replace('<br>', '\n').replace('<br/>', '\n')
                    .replace('<br />', '\n'))
        return re.sub(r'<[^>]+>', '', text).strip()

    def convert_cloze(fields: list):
        front_raw = fields[0] if fields else ''
        back_raw = fields[1] if len(fields) > 1 else ''
        if '{{c' in front_raw:
            question = re.sub(r'\{\{c\d+::(.*?)(?:::[^}]*)?\}\}', '[...]', front_raw)
            answer = re.sub(r'\{\{c\d+::(.*?)(?:::[^}]*)?\}\}', r'\1', front_raw)
            return strip_html(question), strip_html(answer)
        f = strip_html(front_raw)
        b = strip_html(back_raw) if back_raw.strip() else f
        return f, b

    contents = await file.read()
    try:
        with tempfile.TemporaryDirectory() as tmp:
            apkg_path = os.path.join(tmp, 'deck.apkg')
            with open(apkg_path, 'wb') as f:
                f.write(contents)
            with zipfile.ZipFile(apkg_path, 'r') as z:
                names = z.namelist()
                db_name = 'collection.anki21' if 'collection.anki21' in names else 'collection.anki2'
                z.extract(db_name, tmp)
            anki_conn = sqlite3.connect(os.path.join(tmp, db_name))
            anki_conn.row_factory = sqlite3.Row
            created = skipped = 0
            try:
                notes = anki_conn.execute("SELECT flds, tags FROM notes").fetchall()
                for note in notes:
                    fields = note['flds'].split('\x1f')
                    front, back = convert_cloze(fields)
                    if not front or not back:
                        skipped += 1
                        continue
                    tags = [t.strip() for t in (note['tags'] or '').split() if t.strip()]
                    review_repo.create_card(deck_id, front, back, tags=tags, source='apkg')
                    created += 1
            finally:
                anki_conn.close()
            return {'imported': created, 'skipped': skipped, 'source': file.filename}
    except zipfile.BadZipFile:
        raise bad_request('invalid_apkg', 'File is not a valid .apkg (bad zip)')
    except Exception as e:
        raise bad_request('import_failed', f'Import failed: {e}')
