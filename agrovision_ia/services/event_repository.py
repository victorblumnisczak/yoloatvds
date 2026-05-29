import sqlite3
import uuid
from datetime import datetime
from services.config import DB_PATH


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id          TEXT PRIMARY KEY,
                event_time  TEXT,
                label       TEXT,
                confidence  REAL,
                image_path  TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_event_time ON events(event_time)")


def save_event(label: str, confidence: float, image_path: str):
    event_id = uuid.uuid4().hex[:8]
    event_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO events VALUES (?, ?, ?, ?, ?)",
            (event_id, event_time, label, confidence, image_path),
        )
    return event_id, event_time


def list_events(limit: int = 50) -> list:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM events ORDER BY event_time DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def count_events() -> int:
    with sqlite3.connect(DB_PATH) as conn:
        count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    return count
