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
                    event_type TEXT NOT NULL,
                    source_system TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    event_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_source ON events(source_system, source_id)"
            )

    def append(self, events: Iterable[KnowledgeEvent]) -> int:
        inserted = 0
        with self._connect() as connection:
            for event in events:
                try:
                    connection.execute(
                        """
                        INSERT INTO events (
                            event_id, event_type, source_system, source_id,
                            occurred_at, event_json
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            event.event_id,
                            event.event_type,
                            event.source_system,
                            event.source_id,
                            event.occurred_at.isoformat(),
                            event.model_dump_json(),
                        ),
                    )
                    inserted += 1
                except sqlite3.IntegrityError:
                    continue
        return inserted

    def list_events(self) -> list[KnowledgeEvent]:
        with self._connect() as connection:
            rows = connection.execute("SELECT event_json FROM events ORDER BY sequence").fetchall()
        return [KnowledgeEvent.model_validate(json.loads(row["event_json"])) for row in rows]

    def count(self) -> int:
        with self._connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS total FROM events").fetchone()
        return int(row["total"])
