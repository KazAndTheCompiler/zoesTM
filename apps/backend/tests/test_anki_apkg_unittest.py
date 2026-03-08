"""
Anki APKG export/import tests.

These tests verify that decks can be exported to .apkg and re-imported.
"""
import pytest
import base64
import io
import zipfile
from pathlib import Path
import tempfile
from fastapi.testclient import TestClient
from apps.backend.app.main import app

# Use a fresh database per test class
@pytest.fixture(autouse=True)
def setup_test_db():
    # Start with a completely fresh DB to avoid column conflicts
    import sqlite3
    import shutil
    import os
    from apps.backend.app import db
    from pathlib import Path

    # Create fresh temp DB
    tmpdir = tempfile.mkdtemp()
    tmpdb = Path(tmpdir) / "test.apkg.db"

    # Save current DB
    orig = db.DB_PATH

    # Set new DB
    db.DB_PATH = str(tmpdb)

    # Apply migrations fresh
    mig_dir = Path(__file__).resolve().parents[1] / 'migrations'
    with sqlite3.connect(tmpdb) as c:
        for mig in sorted(mig_dir.glob('*.sql')):
            c.executescript(mig.read_text(encoding='utf-8'))

    yield

    # Cleanup
    if tmpdb.exists():
        tmpdb.unlink()
    os.rmdir(tmpdir)
    db.DB_PATH = orig

client = TestClient(app)


def test_export_apkg_success():
    # Create a deck with unique name to avoid duplicates
    import uuid
    deck_name = f"APKG Test Deck {uuid.uuid4().hex[:4]}"
    resp = client.post("/review/decks", params={"name": deck_name})
    if resp.status_code != 200:
        print(f"Error: {resp.text}")
    assert resp.status_code == 200
    deck = resp.json()
    deck_id = deck["id"]

    # Add a card (endpoint expects query params)
    resp = client.post(f"/review/decks/{deck_id}/cards", params={"front": "Q1", "back": "A1", "tags": "test"})
    assert resp.status_code == 200

    # Export as APKG
    resp = client.post(f"/anki-apkg/decks/{deck_id}/export-apkg")
    assert resp.status_code == 200
    data = resp.json()
    assert "filename" in data
    assert data["filename"].endswith(".apkg")
    assert data["encoding"] == "base64"
    raw = base64.b64decode(data["data"])
    assert len(raw) > 0

    # Verify zip contents
    zip_buffer = io.BytesIO(raw)
    with zipfile.ZipFile(zip_buffer, 'r') as z:
        names = z.namelist()
        assert 'collection.anki2/notes1.csv' in names or 'collection.anki2/notes1.csv' in names
        assert 'collection.anki2/models1.json' in names


def test_import_apkg_roundtrip():
    # Create a deck for import
    resp = client.post("/anki-apkg/deck-names")
    # ignore; just ensure endpoint exists

    # We need to create a minimal .apkg with one card
    import uuid
    deck_name = f"import_target_{uuid.uuid4().hex[:4]}"
    resp = client.post("/review/decks", params={"name": deck_name})
    assert resp.status_code == 200
    deck = resp.json()
    target_id = deck["id"]

    # Build minimal APKG in-memory
    import csv
    import json
    import zipfile
    import io
    import uuid
    from datetime import UTC, datetime

    def build_apkg(deck_name, cards_data):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
            z.writestr('collection.anki2/collection.conf', json.dumps({
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
            notes_csv = io.StringIO()
            writer = csv.writer(notes_csv)
            writer.writerow(['id', 'guid', 'mid', 'nfd', 'usn', 'mod', 'tag', 'flds', 'sfld', 'csum', 'flags', 'data', 'dupe', 'model'])
            for i, (front, back, tags) in enumerate(cards_data):
                writer.writerow([
                    i+1,
                    str(uuid.uuid4()),
                    1, 0, 0,
                    int(datetime.now(UTC).timestamp()),
                    '|'.join(tags),
                    f"{front}|||{back}",
                    front, 0, 0, '', 0, 1,
                ])
            z.writestr('collection.anki2/notes1.csv', notes_csv.getvalue())
            z.writestr('collection.anki2/models1.json', json.dumps([{
                'id': 1,
                'name': 'zoesTM card',
                'flds': [{'name': 'Front','ord':0,'sticky':False,'rtl':False,'font':'Liberation Sans,11px'},
                         {'name': 'Back','ord':1,'sticky':False,'rtl':False,'font':'Liberation Sans,11px'}],
                'css': '/* */',
                'tmpls': [{'name':'card1','ord':0,'qfmt':'{{Front}}','afmt':'{{FrontSide}}<hr id=answer>{{Back}}','did':1}],
                'cat': 'zoesTM',
            }]))
            # cards.csv minimal
            cards_csv = io.StringIO()
            writer2 = csv.writer(cards_csv)
            writer2.writerow(['nid','ord','did','mod','usn','due','odue','type','queue','ivl','left','odid','flags','data'])
            for i, _ in enumerate(cards_data):
                writer2.writerow([i+1, 0, 1, int(datetime.now(UTC).timestamp()), 0,
                                  int(datetime.now(UTC).timestamp()) + 86400, 0, 1, 0, 1, 0, 0, 0, ''])
            z.writestr('collection.anki2/cards.csv', cards_csv.getvalue())
        buf.seek(0)
        return buf.read()

    apkg_bytes = build_apkg(deck_name, [("Hello", "World", ["greeting"])])

    # Import via endpoint
    resp = client.post("/anki-apkg/import-apkg", files={"file": ("test.apkg", apkg_bytes, "application/zip")}, data={"target_deck_id": target_id})
    assert resp.status_code == 200, resp.text
    result = resp.json()
    assert result["success"] is True
    assert result["cards_created"] >= 1

    # Verify card exists in API
    resp = client.get(f"/review/decks/{target_id}")
    assert resp.status_code == 200
    d = resp.json()
    cards = review_repo.export_preview(target_id)["cards"]
    assert any(c["front"] == "Hello" for c in cards)
