import json
import sqlite3
import threading
from datetime import datetime, timedelta
from services.scraping.base import ScrapingResult
from services.logging_config import get_logger

log = get_logger("agrovision.scraping.cache")


class ScrapingCache:
    def __init__(self, db_path: str):
        self._db = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self._db) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scraping_cache (
                    cache_key   TEXT PRIMARY KEY,
                    source      TEXT,
                    payload     TEXT,
                    fetched_at  TEXT,
                    expires_at  TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_expires ON scraping_cache(expires_at)")

    def _row_to_result(self, row) -> ScrapingResult:
        payload = json.loads(row["payload"]) if row["payload"] else {}
        return ScrapingResult(
            source=row["source"],
            fetched_at=datetime.fromisoformat(row["fetched_at"]),
            payload=payload,
        )

    def get(self, key: str) -> ScrapingResult | None:
        now = datetime.now().isoformat()
        with self._lock, sqlite3.connect(self._db) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM scraping_cache WHERE cache_key=? AND expires_at > ?",
                (key, now),
            ).fetchone()
            return self._row_to_result(row) if row else None

    def get_stale(self, key: str) -> ScrapingResult | None:
        with self._lock, sqlite3.connect(self._db) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM scraping_cache WHERE cache_key=?", (key,)
            ).fetchone()
            return self._row_to_result(row) if row else None

    def set(self, key: str, result: ScrapingResult, ttl_seconds: int) -> None:
        expires_at = (result.fetched_at + timedelta(seconds=ttl_seconds)).isoformat()
        payload_json = json.dumps(result.payload, ensure_ascii=False, default=str)
        with self._lock, sqlite3.connect(self._db) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO scraping_cache VALUES (?, ?, ?, ?, ?)",
                (key, result.source, payload_json, result.fetched_at.isoformat(), expires_at),
            )

    def delete(self, key: str) -> None:
        with self._lock, sqlite3.connect(self._db) as conn:
            conn.execute("DELETE FROM scraping_cache WHERE cache_key=?", (key,))

    def stats(self) -> dict:
        with self._lock, sqlite3.connect(self._db) as conn:
            conn.row_factory = sqlite3.Row
            total = conn.execute("SELECT COUNT(*) AS n FROM scraping_cache").fetchone()["n"]
            by_source = {
                r["source"]: r["n"]
                for r in conn.execute("SELECT source, COUNT(*) AS n FROM scraping_cache GROUP BY source")
            }
            return {"total": total, "by_source": by_source}
