from __future__ import annotations

from collections.abc import Callable

from knowledge_architect.application.commands import SyncSourceArtifactCommand
from knowledge_architect.application.results import SyncSourceArtifactResult
from knowledge_architect.connectors.notion import NotionConnector
from knowledge_architect.event_store import SQLiteEventStore


class SyncSourceArtifactHandler:
    """Orchestrate source acquisition, event creation, and persistence.

    This first application-layer boundary intentionally preserves the v0.1
    connector and event-store contracts. Future RFCs will replace the concrete
    dependencies with ports without changing the CLI contract introduced here.
    """

    def __init__(
        self,
        connector: NotionConnector,
        event_store: SQLiteEventStore,
        event_factory: Callable | None = None,
    ) -> None:
        self._connector = connector
        self._event_store = event_store
        self._event_factory = event_factory or connector.to_event

    def handle(self, command: SyncSourceArtifactCommand) -> SyncSourceArtifactResult:
        document = self._connector.fetch(command.source_id)
        event = self._event_factory(document)
        inserted = self._event_store.append([event])
        return SyncSourceArtifactResult(
            inserted=inserted,
            source_system=document.source_system,
            source_id=document.source_id,
            title=document.title,
        )
