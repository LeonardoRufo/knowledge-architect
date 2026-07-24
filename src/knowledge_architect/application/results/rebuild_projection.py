from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class RebuildProjectionResult:
    projection_name: str
    projection_version: int
    events_replayed: int
    last_sequence: int
    state: dict[str, Any]
