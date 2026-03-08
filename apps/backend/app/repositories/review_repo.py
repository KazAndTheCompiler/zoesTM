import csv
import io
import json
import uuid
from datetime import UTC, datetime, timedelta
from ..db import conn, tx
from ..services.spaced import compute_next_interval


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def list_decks():
    with conn() as c:
        rows = c.execute("SELECT id,name,created_at,updated_at FROM decks ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


def get_deck_by_name(name: str):
    """Find a deck by its name (case-insensitive)."""
    with conn() as c:
        row = c.execute("SELECT id,name,created_at,updated_at FROM decks WHERE lower(name)=lower(?)", (name.strip(),)).fetchone()
    return dict(row) if row else None


def get_all_cards_for_export(deck_id: str):
    """Return all cards in a deck for APKG export (including needed fields)."""
    with conn() as c:
        rows = c.execute(
            """
            SELECT id,front,back,state,tags,source,ease_factor,last_interval_days,next_review_at,last_rating,lapse_count,reviews_done,suspended,buried_until,created_at,updated_at
            FROM cards WHERE deck_id=?
            ORDER BY created_at ASC
            """,
            (deck_id,),
        ).fetchall()
    cards = []
    for r in rows:
        d = dict(r)
        d['tags'] = json.loads(d.get('tags') or '[]')
        cards.append(d)
    return cards


def delete_card(card_id: str):
    """Delete a card by ID."""
    with tx() as c:
        c.execute("DELETE FROM cards WHERE id=?", (card_id,))
    return {'deleted': True}


def create_deck(name: str):
    normalized = (name or '').strip()
    if len(normalized) < 2 or len(normalized) > 80:
        raise ValueError('deck name must be 2..80 chars')
    with conn() as c:
        exists = c.execute("SELECT id FROM decks WHERE lower(name)=lower(?)", (normalized,)).fetchone()
        if exists:
            raise LookupError('deck name already exists')
    did = str(uuid.uuid4())
    with tx() as c:
        c.execute("INSERT INTO decks(id,name) VALUES(?,?)", (did, normalized))
    return get_deck(did)


def get_deck(deck_id: str):
    with conn() as c:
        row = c.execute("SELECT id,name,created_at,updated_at FROM decks WHERE id=?", (deck_id,)).fetchone()
    return dict(row) if row else None


def create_card(deck_id: str, front: str, back: str, tags: list[str] | None = None, source: str = 'manual'):
    cid = str(uuid.uuid4())
    tags_json = json.dumps(tags or [])
    with tx() as c:
        c.execute(
            "INSERT INTO cards(id,deck_id,front,back,state,next_review_at,tags,source,suspended,buried_until) VALUES(?,?,?,?,?,?,?,?,0,NULL)",
            (cid, deck_id, front, back, 'new', _now_iso(), tags_json, source),
        )
    return get_card(cid)


def get_card(card_id: str):
    with conn() as c:
        row = c.execute("SELECT * FROM cards WHERE id=?", (card_id,)).fetchone()
    if not row:
        return None
    out = dict(row)
    out['tags'] = json.loads(out.get('tags') or '[]')
    return out


def set_card_flags(card_id: str, *, suspend: bool | None = None, bury_until: str | None = None):
    with tx() as c:
        if suspend is not None:
            c.execute("UPDATE cards SET suspended=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", (1 if suspend else 0, card_id))
        if bury_until is not None:
            c.execute("UPDATE cards SET buried_until=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", (bury_until, card_id))
    return get_card(card_id)


def due_cards(limit: int = 20, deck_id: str | None = None):
    now = _now_iso()
    params: list[object] = [now, now]
    deck_clause = ''
    if deck_id:
        deck_clause = ' AND deck_id=?'
        params.append(deck_id)
    params.append(max(1, min(limit, 200)))
    with conn() as c:
        rows = c.execute(
            """
            SELECT * FROM cards
            WHERE suspended=0
            AND (buried_until IS NULL OR buried_until <= ?)
            AND (next_review_at IS NULL OR next_review_at <= ?)
            """ + deck_clause + """
            ORDER BY CASE state WHEN 'learning' THEN 0 WHEN 'relearn' THEN 1 WHEN 'review' THEN 2 ELSE 3 END, next_review_at ASC
            LIMIT ?
            """,
            tuple(params),
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d['tags'] = json.loads(d.get('tags') or '[]')
        out.append(d)
    return out


def apply_rating(card_id: str, rating: str):
    """Apply a rating to a card and update its state, interval, ease factor, and counters."""
    card = get_card(card_id)
    if not card:
        raise ValueError('card not found')

    # Current values (with sensible defaults for new cards)
    current_state = card['state']
    current_interval = card.get('last_interval_days') or 1  # days until previous next review
    current_ease = card.get('ease_factor') or 2.5
    reviews_done = card.get('reviews_done') or 0
    lapse_count = card.get('lapse_count') or 0

    # Compute new values using SM-2 algorithm
    result = compute_next_interval(current_state, rating, current_interval, current_ease, reviews_done)
    new_state = result['new_state']
    new_interval = result['new_interval']
    new_ease = result['new_ease_factor']
    lapse_increment = result['lapse_increment']

    # Compute next review date
    next_at = (datetime.now(UTC) + timedelta(days=max(0, new_interval))).isoformat()

    with tx() as c:
        c.execute(
            """
            UPDATE cards
            SET state=?, next_review_at=?, last_rating=?, ease_factor=?, last_interval_days=?, lapse_count=?, reviews_done=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (new_state, next_at, rating, new_ease, new_interval, lapse_count + (1 if lapse_increment else 0), reviews_done + 1, card_id),
        )
    return get_card(card_id)


def import_notes(deck_id: str, source_text: str, fmt: str = 'csv'):
    sep = '\t' if fmt == 'tsv' else ','
    reader = csv.DictReader(io.StringIO(source_text), delimiter=sep)
    created = 0
    for row in reader:
        front = (row.get('front') or '').strip()
        back = (row.get('back') or '').strip()
        if not front or not back:
            continue
        tags = [x.strip() for x in (row.get('tags') or '').split('|') if x.strip()]
        create_card(deck_id, front, back, tags=tags, source=(row.get('source') or 'import'))
        created += 1
    return {'created_cards': created}


def export_preview(deck_id: str, limit: int = 50):
    with conn() as c:
        rows = c.execute("SELECT id,front,back,state,next_review_at,tags,source,suspended,buried_until FROM cards WHERE deck_id=? ORDER BY created_at DESC LIMIT ?", (deck_id, max(1, min(limit, 200)))).fetchall()
    cards = []
    for r in rows:
        d = dict(r)
        d['tags'] = json.loads(d.get('tags') or '[]')
        cards.append(d)
    return {'deck_id': deck_id, 'card_count': len(cards), 'cards': cards}
