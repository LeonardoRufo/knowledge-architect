from __future__ import annotations

from knowledge_architect.application.commands.rebuild_projection import (
    RebuildProjectionCommand,
)
from knowledge_architect.application.results.rebuild_projection import (
    RebuildProjectionResult,
)
from knowledge_architect.ports import EventStorePort, ProjectionStorePort
from knowledge_architect.projections import ProjectionRegistry


class RebuildProjectionHandler:
    """Rebuild a projection exclusively from the ordered immutable event stream."""

    def __init__(
        self,
        *,
        event_store: EventStorePort,
        projection_store: ProjectionStorePort,
        registry: ProjectionRegistry,
    ) -> None:
        self._event_store = event_store
        self._projection_store = projection_store
        self._registry = registry

    def handle(self, command: RebuildProjectionCommand) -> RebuildProjectionResult:
        projection = self._registry.get(command.projection_name)
        state = projection.initial_state()
        stream = self._event_store.list_stream()

        for stored_event in stream:
            state = projection.apply(state, stored_event.event)

        finalized_state = projection.finalize(state)
        last_sequence = stream[-1].sequence if stream else 0
        self._projection_store.replace(
            name=projection.name,
            version=projection.version,
            last_sequence=last_sequence,
            state=finalized_state,
        )
        return RebuildProjectionResult(
            projection_name=projection.name,
            projection_version=projection.version,
            events_replayed=len(stream),
            last_sequence=last_sequence,
            state=finalized_state,
        )
