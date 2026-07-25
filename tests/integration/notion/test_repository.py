from __future__ import annotations

from uuid import uuid4

import pytest

from knowledge_architect.integrations.notion import (
    NotionKnowledgeUnit,
    NotionKnowledgeUnitRepository,
    NotionSynchronizer,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.notion,
]


def make_unit() -> NotionKnowledgeUnit:
    unique_id = uuid4()

    return NotionKnowledgeUnit(
        name="Teste automatizado do Knowledge Architect",
        kir_id=f"ku-pytest-{unique_id}",
        revision_id=f"rev-{uuid4()}",
        kind="Concept",
        status="Draft",
        sync_hash=f"pytest-{unique_id}",
        managed_by_kir=True,
    )


def test_creates_and_reads_knowledge_unit(
    notion_repository: NotionKnowledgeUnitRepository,
) -> None:
    expected = make_unit()
    created = None

    try:
        created = notion_repository.create(expected)

        assert created.page_id is not None
        assert created.kir_id == expected.kir_id
        assert created.name == expected.name
        assert created.revision_id == expected.revision_id
        assert created.kind == expected.kind
        assert created.status == expected.status
        assert created.sync_hash == expected.sync_hash

        loaded = notion_repository.get_by_kir_id(expected.kir_id)

        assert loaded.page_id == created.page_id
        assert loaded.comparison_state() == expected.comparison_state()

    finally:
        if created is not None:
            notion_repository.archive(created)


def test_upsert_updates_existing_page(
    notion_repository: NotionKnowledgeUnitRepository,
) -> None:
    initial = make_unit()
    saved = None

    try:
        first_action, saved = notion_repository.upsert(initial)

        updated = NotionKnowledgeUnit(
            name="Teste automatizado atualizado",
            kir_id=initial.kir_id,
            revision_id=f"rev-{uuid4()}",
            kind=initial.kind,
            status="Published",
            sync_hash=f"{initial.sync_hash}-updated",
            managed_by_kir=True,
            page_id=saved.page_id,
        )

        second_action, result = notion_repository.upsert(updated)

        assert first_action == "created"
        assert second_action == "updated"
        assert result.page_id == saved.page_id
        assert result.kir_id == initial.kir_id
        assert result.name == "Teste automatizado atualizado"
        assert result.status == "Published"
        assert result.revision_id == updated.revision_id

        saved = result

    finally:
        if saved is not None:
            notion_repository.archive(saved)


def test_detects_external_modification(
    notion_repository: NotionKnowledgeUnitRepository,
    notion_synchronizer: NotionSynchronizer,
) -> None:
    expected = make_unit()
    created = None

    try:
        created = notion_repository.create(expected)

        externally_modified = NotionKnowledgeUnit(
            name="Título alterado externamente",
            kir_id=created.kir_id,
            revision_id=created.revision_id,
            kind=created.kind,
            status=created.status,
            sync_hash=created.sync_hash,
            managed_by_kir=created.managed_by_kir,
            source=created.source,
            parent_ids=created.parent_ids,
            page_id=created.page_id,
        )

        notion_repository.update(externally_modified)

        result = notion_synchronizer.compare(expected)

        assert result.status == "conflict"
        assert result.has_conflict is True
        assert len(result.differences) == 1

        difference = result.differences[0]

        assert difference.field == "name"
        assert difference.expected == expected.name
        assert difference.actual == "Título alterado externamente"

    finally:
        if created is not None:
            notion_repository.archive(created)
