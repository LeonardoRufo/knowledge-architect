from dataclasses import FrozenInstanceError

import pytest

from knowledge_architect.kir import (
    Ancestors,
    And,
    Descendants,
    Equals,
    HasEvidence,
    HasRelation,
    HasTransformation,
    KindIs,
    NamespaceIs,
    Neighbors,
    Not,
    NotEquals,
    Or,
    Ordering,
    OrderingDirection,
    Pagination,
    Parents,
    Projection,
    Query,
    QueryEngine,
    QueryResult,
    ShortestPath,
    canonical_json,
)
from knowledge_architect.kir.identity import EntityId


def test_query_is_immutable_and_serializable() -> None:
    query = Query(
        predicate=And((KindIs("knowledge_unit"), NamespaceIs("biology"))),
        ordering=(Ordering("identity"),),
        projection=Projection(("identity", "namespace")),
        pagination=Pagination(limit=25),
    )

    with pytest.raises(FrozenInstanceError):
        query.predicate = None  # type: ignore[misc]

    assert canonical_json(query) == (
        '{"ordering":[{"direction":"ascending","field":"identity"}],'
        '"origin":[],"pagination":{"limit":25,"offset":0},'
        '"predicate":{"predicates":[{"kind":"knowledge_unit"},'
        '{"namespace":"biology"}]},'
        '"projection":{"fields":["identity","namespace"]},"traversal":null}'
    )


def test_predicates_are_composable_and_immutable() -> None:
    predicate = Or(
        (
            Equals("namespace", "biology"),
            And(
                (
                    NotEquals("kind", "draft"),
                    Not(HasEvidence()),
                )
            ),
        )
    )
    assert isinstance(predicate.predicates[1], And)
    with pytest.raises(ValueError, match="at least two"):
        And((KindIs("entity"),))
    with pytest.raises(ValueError, match="at least two"):
        Or(())


def test_domain_predicates_capture_query_intent() -> None:
    assert HasRelation("supports").relation_kind == "supports"
    assert HasEvidence("observation").evidence_kind == "observation"
    assert HasTransformation("merge").transformation_kind == "merge"
    with pytest.raises(ValueError, match="must not be empty"):
        NamespaceIs("  ")


def test_traversals_require_origin_and_validate_depth() -> None:
    origin = EntityId.new()
    assert Query(origin=(origin,), traversal=Parents()).origin == (origin,)
    assert Query(origin=(origin,), traversal=Neighbors("supports")).traversal == Neighbors(
        "supports"
    )
    assert Query(origin=(origin,), traversal=Ancestors(3)).traversal == Ancestors(3)
    assert Query(origin=(origin,), traversal=Descendants()).traversal == Descendants()
    target = EntityId.new()
    assert Query(origin=(origin,), traversal=ShortestPath(target)).traversal == ShortestPath(
        target
    )
    with pytest.raises(ValueError, match="require at least one origin"):
        Query(traversal=Parents())
    with pytest.raises(ValueError, match="at least 1"):
        Ancestors(0)


def test_query_composition_returns_new_instances() -> None:
    base = Query(predicate=KindIs("knowledge_unit"))
    filtered = base.where(NamespaceIs("biology"))
    projected = filtered.project("identity", "namespace")
    ordered = projected.order_by(
        Ordering("namespace"), Ordering("identity", OrderingDirection.DESCENDING)
    )
    paginated = ordered.paginate(offset=10, limit=5)

    assert base.predicate == KindIs("knowledge_unit")
    assert filtered.predicate == And((KindIs("knowledge_unit"), NamespaceIs("biology")))
    assert projected.projection.fields == ("identity", "namespace")
    assert ordered.ordering[1].direction is OrderingDirection.DESCENDING
    assert paginated.pagination == Pagination(10, 5)


def test_query_validates_deterministic_declarations() -> None:
    identity = EntityId.new()
    with pytest.raises(ValueError, match="origin identities must be unique"):
        Query(origin=(identity, identity))
    with pytest.raises(ValueError, match="ordering field"):
        Query(ordering=(Ordering("identity"), Ordering("identity")))
    with pytest.raises(ValueError, match="projection fields must be unique"):
        Projection(("identity", "identity"))
    with pytest.raises(ValueError, match="offset"):
        Pagination(offset=-1)
    with pytest.raises(ValueError, match="limit"):
        Pagination(limit=0)


def test_query_result_normalizes_metadata_and_statistics() -> None:
    result = QueryResult(
        elements=("b", "a"),
        metadata=(("query_id", "q-1"), ("backend", "memory")),
        statistics=(("visited", 4), ("returned", 2)),
    )
    assert result.elements == ("b", "a")
    assert result.metadata == (("backend", "memory"), ("query_id", "q-1"))
    assert result.statistics == (("returned", 2), ("visited", 4))
    assert result.metadata_value("backend") == "memory"
    assert result.statistic("returned") == 2
    assert canonical_json(result).startswith('{"elements":["b","a"],"metadata":')
    with pytest.raises(ValueError, match="unique"):
        QueryResult(metadata=(("backend", "memory"), ("backend", "sql")))


def test_query_engine_contract_is_backend_independent() -> None:
    class MemoryEngine(QueryEngine):
        def execute(self, query: Query) -> QueryResult:
            return QueryResult(
                elements=(query,),
                metadata=(("engine", "memory"),),
            )

    query = Query(predicate=KindIs("entity"))
    result = MemoryEngine().execute(query)
    assert result.elements == (query,)
    assert result.metadata_value("engine") == "memory"
    with pytest.raises(TypeError):
        QueryEngine()
