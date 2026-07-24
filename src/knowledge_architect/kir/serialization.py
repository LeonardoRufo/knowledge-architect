from __future__ import annotations

import json
from dataclasses import fields, is_dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from .identity import KIRIdentity


def to_primitive(value: Any) -> Any:
    """Convert KIR values into deterministic JSON-compatible primitives."""

    if isinstance(value, KIRIdentity):
        return value.value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: to_primitive(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, dict):
        items = sorted(value.items(), key=lambda item: str(item[0]))
        return {str(key): to_primitive(item) for key, item in items}
    if isinstance(value, (tuple, list)):
        return [to_primitive(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"Unsupported KIR serialization value: {type(value).__name__}")


def canonical_json(value: Any) -> str:
    """Serialize a KIR value using stable key order and compact separators."""

    return json.dumps(
        to_primitive(value),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
