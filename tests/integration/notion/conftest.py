from __future__ import annotations

import pytest

from knowledge_architect.integrations.notion import (
    NotionClient,
    NotionKnowledgeUnitRepository,
    NotionSynchronizer,
)


@pytest.fixture(scope="session")
def notion_client() -> NotionClient:
    return NotionClient()


@pytest.fixture(scope="session")
def notion_repository(
    notion_client: NotionClient,
) -> NotionKnowledgeUnitRepository:
    return NotionKnowledgeUnitRepository(notion_client)


@pytest.fixture(scope="session")
def notion_synchronizer(
    notion_repository: NotionKnowledgeUnitRepository,
) -> NotionSynchronizer:
    return NotionSynchronizer(notion_repository)
