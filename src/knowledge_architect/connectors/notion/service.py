from __future__ import annotations

from knowledge_architect.connectors.notion.client import NotionClient
from knowledge_architect.core import SourceDocument


class NotionConnector:
    """Read-only source adapter for Notion."""

    def __init__(self, client: NotionClient) -> None:
        self.client = client

    def discover(self, query: str | None = None) -> list[dict]:
        return self.client.search(query)

    def fetch(self, source_id: str) -> SourceDocument:
        return self.client.fetch_page(source_id)
