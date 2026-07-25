from __future__ import annotations

from .models import (
    NotionKnowledgeUnit,
    SyncDifference,
    SyncResult,
)
from .repository import NotionKnowledgeUnitRepository


class NotionSynchronizer:
    def __init__(
        self,
        repository: NotionKnowledgeUnitRepository,
    ) -> None:
        self.repository = repository

    def compare(
        self,
        expected: NotionKnowledgeUnit,
    ) -> SyncResult:
        actual = self.repository.get_by_kir_id(expected.kir_id)

        expected_state = expected.comparison_state()
        actual_state = actual.comparison_state()

        differences: list[SyncDifference] = []

        for field, expected_value in expected_state.items():
            actual_value = actual_state[field]

            if actual_value != expected_value:
                differences.append(
                    SyncDifference(
                        field=field,
                        expected=expected_value,
                        actual=actual_value,
                    )
                )

        return SyncResult(
            status="conflict" if differences else "synchronized",
            notion_unit=actual,
            differences=tuple(differences),
        )