from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class SQLiteProjectionStore:
    """SQLite snapshot store for named, versioned materialized projections."""

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
                CREATE TABLE IF NOT EXISTS projections (
                    name TEXT PRIMARY KEY,
                    version INTEGER NOT NULL,
                    last_sequence INTEGER NOT NULL,
                    state_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def replace(
        self,
        *,
        name: str,
        version: int,
        last_sequence: int,
        state: dict[str, Any],
    ) -> None:
        state_json = json.dumps(state, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO projections (name, version, last_sequence, state_json)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    version = excluded.version,
                    last_sequence = excluded.last_sequence,
                    state_json = excluded.state_json,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (name, version, last_sequence, state_json),
            )

    def load(self, name: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT name, version, last_sequence, state_json, updated_at
                FROM projections
                WHERE name = ?
                """,
                (name,),
            ).fetchone()
        if row is None:
            return None
        return {
            "name": row["name"],
            "version": row["version"],
            "last_sequence": row["last_sequence"],
            "state": json.loads(row["state_json"]),
            "updated_at": row["updated_at"],
        }
