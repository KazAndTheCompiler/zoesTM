"""
Seed script — run once after migrate.py to populate demo data.
Usage: python apps/backend/scripts/seed.py
       python apps/backend/scripts/seed.py --force   (wipe + re-seed)
"""
import sys
import uuid
from pathlib import Path
from datetime import datetime, timedelta, UTC

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from apps.backend.app.db import tx, conn  # noqa: E402


def already_seeded(c) -> bool:
    row = c.execute("SELECT COUNT(*) FROM tasks").fetchone()
    return row[0] > 0


def seed_tasks(c):
    now = datetime.now(UTC)
    tasks = [
        (str(uuid.uuid4()), "Review project proposal", (now + timedelta(hours=2)).isoformat(), 1),
        (str(uuid.uuid4()), "Write unit tests for auth module", (now + timedelta(days=1)).isoformat(), 2),
        (str(uuid.uuid4()), "Buy groceries", (now + timedelta(days=2)).isoformat(), 3),
        (str(uuid.uuid4()), "Read ML paper on transformers", (now + timedelta(days=3)).isoformat(), 2),
        (str(uuid.uuid4()), "Email weekly update to team", (now + timedelta(hours=5)).isoformat(), 1),
        (str(uuid.uuid4()), "Clean up old branches in repo", None, 4),
    ]
    for tid, title, due_at, priority in tasks:
        c.execute(
            "INSERT OR IGNORE INTO tasks(id, title, due_at, priority, done) VALUES(?,?,?,?,0)",
            (tid, title, due_at, priority),
        )
    print(f"  Seeded {len(tasks)} tasks")


def seed_habits(c):
    now = datetime.now(UTC)
    habit_names = ["hydration", "morning-walk", "reading"]
    for name in habit_names:
        c.execute(
            "INSERT OR IGNORE INTO habits(id, name) VALUES(?,?)",
            (str(uuid.uuid4()), name),
        )

    # Try to seed logs; table may have different schema depending on migration state
    try:
        for name in habit_names:
            for days_back in range(7):
                logged_at = (now - timedelta(days=days_back)).isoformat()
                done = 0 if days_back == 3 else 1
                c.execute(
                    "INSERT OR IGNORE INTO habit_logs(id, habit_name, done, logged_at) VALUES(?,?,?,?)",
                    (str(uuid.uuid4()), name, done, logged_at),
                )
        print(f"  Seeded {len(habit_names)} habits with 7 days of logs")
    except Exception as exc:
        print(f"  Seeded {len(habit_names)} habits (log table not available: {exc})")


def seed_review(c):
    now = datetime.now(UTC)
    review_seed = {
        "General Knowledge": [
            ("What is spaced repetition?", "A learning technique that increases intervals between reviews as knowledge strengthens."),
            ("What is the capital of France?", "Paris."),
            ("What does HTTP stand for?", "HyperText Transfer Protocol."),
        ],
        "Programming": [
            ("What does O(n log n) mean?", "Time scales by n × log(n) — typical of efficient sorting algorithms like merge sort."),
            ("What is a closure?", "A function that retains access to variables from its enclosing scope after that scope exits."),
            ("What is a foreign key?", "A column referencing the primary key of another table, enforcing referential integrity."),
        ],
    }

    created_decks = 0
    created_cards = 0
    for deck_name, cards in review_seed.items():
        deck_row = c.execute("SELECT id FROM decks WHERE lower(name)=lower(?)", (deck_name,)).fetchone()
        deck_id = deck_row[0] if deck_row else str(uuid.uuid4())
        if not deck_row:
            c.execute("INSERT INTO decks(id, name) VALUES(?,?)", (deck_id, deck_name))
            created_decks += 1

        for front, back in cards:
            exists = c.execute(
                "SELECT id FROM cards WHERE deck_id=? AND front=?",
                (deck_id, front),
            ).fetchone()
            if exists:
                continue
            c.execute(
                "INSERT INTO cards(id, deck_id, front, back, state, next_review_at) VALUES(?,?,?,?,?,?)",
                (str(uuid.uuid4()), deck_id, front, back, "new", now.isoformat()),
            )
            created_cards += 1

    total_decks = len(review_seed)
    total_cards = sum(len(v) for v in review_seed.values())
    print(f"  Review demo ensured: {total_decks} decks / {total_cards} cards ({created_decks} decks and {created_cards} cards added)")


def seed_alarms(c):
    alarms = [
        ("07:00", "Wake up"),
        ("12:30", "Lunch break"),
        ("17:00", "End of workday"),
    ]
    for alarm_time, title in alarms:
        aid = str(uuid.uuid4())
        c.execute(
            "INSERT OR IGNORE INTO alarms(id, alarm_time, enabled) VALUES(?,?,1)",
            (aid, alarm_time),
        )
        # meta table carries title/kind fields in current schema
        try:
            c.execute(
                "INSERT OR REPLACE INTO alarm_meta(alarm_id, kind, title, tts_text, youtube_link) VALUES(?,?,?,?,?)",
                (aid, 'alarm', title, title, ''),
            )
        except Exception:
            # If alarm_meta migration has not been applied yet, keep core alarm seed.
            pass
    print(f"  Seeded {len(alarms)} alarms")


def main():
    print("Running seed...")
    with conn() as c:
        seeded = already_seeded(c)

    with tx() as c:
        if seeded and "--force" not in sys.argv:
            print("  Core data already seeded — ensuring review demo deck/cards")
            seed_review(c)
            print("Seed complete.")
            return

        seed_tasks(c)
        seed_habits(c)
        seed_review(c)
        seed_alarms(c)

    print("Seed complete.")


if __name__ == "__main__":
    if "--force" in sys.argv:
        with tx() as c:
            for tbl in ("tasks", "cards", "decks", "alarms"):
                try:
                    c.execute(f"DELETE FROM {tbl}")
                except Exception:
                    pass
        print("Cleared existing data (--force)")
    main()
