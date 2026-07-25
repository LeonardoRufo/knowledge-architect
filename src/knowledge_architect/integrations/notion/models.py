from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class NotionKnowledgeUnit:
    name: str
    kir_id: str
    revision_id: str
    kind: str
    status: str
    sync_hash: str
    managed_by_kir: bool = True
    source: str | None = None
    parent_ids: tuple[str, ...] = ()
    page_id: str | None = None

    def comparison_state(self) -> dict[str, Any]:
        """Retorna somente os campos relevantes para sincronização."""
        return {
            "name": self.name,
            "kir_id": self.kir_id,
            "revision_id": self.revision_id,
            "kind": self.kind,
            "status": self.status,
            "sync_hash": self.sync_hash,
            "managed_by_kir": self.managed_by_kir,
            "source": self.source,
            "parent_ids": self.parent_ids,
        }


@dataclass(frozen=True, slots=True)
class SyncDifference:
    field: str
    expected: Any
    actual: Any


@dataclass(frozen=True, slots=True)
class SyncResult:
    status: str
    notion_unit: NotionKnowledgeUnit
    differences: tuple[SyncDifference, ...] = ()

    @property
    def has_conflict(self) -> bool:
        return bool(self.differences)