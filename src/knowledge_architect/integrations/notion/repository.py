from __future__ import annotations

from .client import NotionClient
from .exceptions import (
    DuplicateNotionUnitError,
    NotionUnitNotFoundError,
)
from .mapper import notion_page_to_unit, unit_to_notion_properties
from .models import NotionKnowledgeUnit


class NotionKnowledgeUnitRepository:
    def __init__(self, client: NotionClient) -> None:
        self.client = client

    def find_by_kir_id(
        self,
        kir_id: str,
    ) -> NotionKnowledgeUnit | None:
        results = self.client.query_by_kir_id(kir_id)

        if len(results) > 1:
            raise DuplicateNotionUnitError(
                f"Foram encontradas {len(results)} páginas "
                f"com o KIR ID {kir_id}."
            )

        if not results:
            return None

        return notion_page_to_unit(results[0])

    def get_by_kir_id(
        self,
        kir_id: str,
    ) -> NotionKnowledgeUnit:
        unit = self.find_by_kir_id(kir_id)

        if unit is None:
            raise NotionUnitNotFoundError(
                f"Knowledge Unit não encontrada: {kir_id}"
            )

        return unit

    def create(
        self,
        unit: NotionKnowledgeUnit,
    ) -> NotionKnowledgeUnit:
        page = self.client.create_page(
            properties=unit_to_notion_properties(unit),
            children=[
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": (
                                        "Página gerenciada pelo "
                                        "Knowledge Architect."
                                    )
                                },
                            }
                        ]
                    },
                }
            ],
        )

        return notion_page_to_unit(page)

    def update(
        self,
        unit: NotionKnowledgeUnit,
    ) -> NotionKnowledgeUnit:
        if not unit.page_id:
            raise ValueError(
                "A unidade precisa de page_id para ser atualizada."
            )

        page = self.client.update_page(
            page_id=unit.page_id,
            properties=unit_to_notion_properties(unit),
        )

        return notion_page_to_unit(page)

    def upsert(
        self,
        unit: NotionKnowledgeUnit,
    ) -> tuple[str, NotionKnowledgeUnit]:
        existing = self.find_by_kir_id(unit.kir_id)

        if existing is None:
            return "created", self.create(unit)

        unit_with_page_id = NotionKnowledgeUnit(
            name=unit.name,
            kir_id=unit.kir_id,
            revision_id=unit.revision_id,
            kind=unit.kind,
            status=unit.status,
            sync_hash=unit.sync_hash,
            managed_by_kir=unit.managed_by_kir,
            source=unit.source,
            parent_ids=unit.parent_ids,
            page_id=existing.page_id,
        )

        return "updated", self.update(unit_with_page_id)

    def archive(
        self,
        unit: NotionKnowledgeUnit,
    ) -> None:
        if not unit.page_id:
            raise ValueError(
                "A unidade precisa de page_id para ser arquivada."
            )

        self.client.archive_page(unit.page_id)
