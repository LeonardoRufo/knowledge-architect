from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    notion_token: str
    notion_version: str
    store_path: str

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        return cls(
            notion_token=os.getenv("NOTION_TOKEN", ""),
            notion_version=os.getenv("NOTION_VERSION", "2026-03-11"),
            store_path=os.getenv("KAA_STORE_PATH", "./data/events.sqlite3"),
        )
