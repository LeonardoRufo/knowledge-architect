from __future__ import annotations

from knowledge_architect.application.commands import SyncSourceArtifactCommand
from knowledge_architect.application.results import SyncSourceArtifactResult
from knowledge_architect.ports import EventFactoryPort, EventStorePort, SourceProviderPort


class SyncSourceArtifactHandler:
    """Orchestrate source acquisition, event creation, and persistence.

    The application layer depends only on ports. Concrete infrastructure is
    selected by an interface adapter, such as the CLI composition root.
    """

    def __init__(
        self,
        source_provider: SourceProviderPort,
        event_store: EventStorePort,
        event_factory: EventFactoryPort,
    ) -> None:
        self._source_provider = source_provider
        self._event_store = event_store
        self._event_factory = event_factory

    def handle(self, command: SyncSourceArtifactCommand) -> SyncSourceArtifactResult:
        document = self._source_provider.fetch(command.source_id)
        event = self._event_factory(document)
        inserted = self._event_store.append([event])
        return SyncSourceArtifactResult(
            inserted=inserted,
            source_system=document.source_system,
            source_id=document.source_id,
            title=document.title,
        )
