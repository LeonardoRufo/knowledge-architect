from __future__ import annotations

import hashlib

from knowledge_architect.connectors.notion.client import NotionClient
from knowledge_architect.core import KnowledgeEvent, SourceDocument


class NotionConnector:
    def __init__(self, client: NotionClient) -> None:
        self.client = client

    def discover(self, query: str | None = None) -> list[dict]:
        return self.client.search(query)

    def fetch(self, source_id: str) -> SourceDocument:
        return self.client.fetch_page(source_id)

    def to_event(self, document: SourceDocument) -> KnowledgeEvent:
        content_hash = hashlib.sha256(document.content_markdown.encode("utf-8")).hexdigest()
        return KnowledgeEvent(
            event_type="source_document_observed",
            source_system=document.source_system,
            source_id=document.source_id,
            payload={
                "title": document.title,
                "url": document.url,
                "last_edited_time": (
                    document.last_edited_time.isoformat() if document.last_edited_time else None
                ),
                "content_markdown": document.content_markdown,
                "content_sha256": content_hash,
                "metadata": document.raw_metadata,
            },
        )
