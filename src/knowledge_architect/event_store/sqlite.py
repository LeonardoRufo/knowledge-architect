from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from pathlib import Path

from knowledge_architect.core import KnowledgeEvent


class SQLiteEventStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL UNIQUE,
                    idempotency_key TEXT,
                    content_fingerprint TEXT,
                    event_type TEXT NOT NULL,
                    source_system TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    event_json TEXT NOT NULL
                )
                """
            )
            self._migrate_columns(connection)
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_source "
                "ON events(source_system, source_id)"
            )
            connection.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_events_idempotency "
                "ON events(idempotency_key) WHERE idempotency_key IS NOT NULL"
            )

    @staticmethod
    def _migrate_columns(connection: sqlite3.Connection) -> None:
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(events)").fetchall()
        }
        if "idempotency_key" not in columns:
            connection.execute("ALTER TABLE events ADD COLUMN idempotency_key TEXT")
        if "content_fingerprint" not in columns:
            connection.execute("ALTER TABLE events ADD COLUMN content_fingerprint TEXT")

    def append(self, events: Iterable[KnowledgeEvent]) -> int:
        inserted = 0
        with self._connect() as connection:
            for event in events:
                cursor = connection.execute(
                    """
                    INSERT OR IGNORE INTO events (
                        event_id, idempotency_key, content_fingerprint, event_type,
                        source_system, source_id, occurred_at, event_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event.event_id,
                        event.idempotency_key,
                        event.content_fingerprint,
                        event.event_type,
                        event.source_system,
                        event.source_id,
                        event.occurred_at.isoformat(),
                        event.model_dump_json(),
                    ),
                )
                inserted += cursor.rowcount
        return inserted

    def list_events(self) -> list[KnowledgeEvent]:
        with self._connect() as connection:
            rows = connection.execute("SELECT event_json FROM events ORDER BY sequence").fetchall()
        return [KnowledgeEvent.model_validate(json.loads(row["event_json"])) for row in rows]

    def count(self) -> int:
        with self._connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS total FROM events").fetchone()
        return int(row["total"])
