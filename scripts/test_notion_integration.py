from __future__ import annotations

from uuid import uuid4

from knowledge_architect.integrations.notion import (
    NotionClient,
    NotionKnowledgeUnit,
    NotionKnowledgeUnitRepository,
    NotionSynchronizer,
)


def main() -> int:
    client = NotionClient()
    repository = NotionKnowledgeUnitRepository(client)
    synchronizer = NotionSynchronizer(repository)

    expected = NotionKnowledgeUnit(
        name="Teste modular do Knowledge Architect",
        kir_id="ku-modular-integration-test",
        revision_id=f"rev-{uuid4()}",
        kind="Concept",
        status="Draft",
        sync_hash="modular-integration-v1",
        managed_by_kir=True,
    )

    action, saved = repository.upsert(expected)

    print("\n========== UPSERT ==========")
    print("Ação:", action)
    print("Page ID:", saved.page_id)
    print("KIR ID:", saved.kir_id)
    print("Revision ID:", saved.revision_id)

    result = synchronizer.compare(expected)

    print("\n========== SINCRONIZAÇÃO ==========")
    print("Estado:", result.status)

    if result.has_conflict:
        for difference in result.differences:
            print(f"\nCampo: {difference.field}")
            print(f"Esperado: {difference.expected}")
            print(f"Encontrado: {difference.actual}")

        return 2

    print("\n✅ Integração modular validada com sucesso")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())