# Arquitetura

## Estado executável atual

```text
CLI
  ↓
Application Command + Handler
  ↓
NotionConnector (somente leitura)
  ↓
SourceDocument normalizado
  ↓
KnowledgeEvent imutável
  ↓
SQLiteEventStore
  ↓
Materializer
  ↓
Estado observável / exportação JSON
```

A camada de aplicação foi introduzida incrementalmente no RFC-001. Os contratos de portas, a separação de `Observation` e a idempotência serão introduzidos em RFCs posteriores.

## Arquitetura-alvo

```text
Interfaces → Application → Domain → Ports → Adapters
```

As dependências apontam para dentro. A CLI não executa regras de domínio; conectores traduzem sistemas externos; adaptadores implementam capacidades declaradas por portas.

## Fronteiras

- **TKA:** princípios teóricos; não depende de tecnologia.
- **KIR:** representação canônica do estado semântico.
- **KAS:** contratos operacionais e transformações.
- **KAE/KAA:** implementação executável e agente.
- **Connectors:** traduzem fontes externas para documentos normalizados; não definem a semântica do Core.

## Segurança

A versão atual exige apenas `Ler conteúdo` no Notion. Atualização, inserção, comentários e dados de usuários não são necessários. Segredos devem existir apenas no `.env` local, nunca no Git ou em arquivos de distribuição.

## Decisões

As decisões permanentes estão em [`docs/adr`](adr/). Propostas incrementais de implementação estão em [`docs/rfc`](rfc/).

## Application ports (RFC-002)

The synchronization use case now follows dependency inversion:

```text
CLI composition root
        ↓
SyncSourceArtifactHandler
        ↓
SourceProviderPort + EventFactoryPort + EventStorePort
        ↓
NotionConnector + SQLiteEventStore
```

Application handlers must not import concrete connectors or persistence adapters.

## Observation identity

Source synchronization separates occurrence identity from logical identity:

```text
SourceDocument
    ↓
SourceObservation
    ├── observation_id (occurrence)
    ├── content_fingerprint (normalized content)
    └── idempotency_key (logical observation)
    ↓
KnowledgeEvent
    ↓
EventStore (deduplicate by idempotency_key)
```

Connectors acquire and normalize source data. The observation factory owns
fingerprinting and event creation, while the event store enforces idempotency.

## Projection engine

Materialized query state is derived by named, versioned projections. Each projection is a deterministic reducer over `StoredEvent` entries ordered by their persisted sequence. Snapshots record the projection version and the last stream sequence included in the rebuild.

```text
SQLiteEventStore.list_stream()
          ↓
ProjectionRegistry
          ↓
SourceDocumentProjection
          ↓
RebuildProjectionHandler
          ↓
SQLiteProjectionStore
```

Projection snapshots are caches and may always be discarded and rebuilt from the event stream.

## Immutable KIR Core

RFC-005 introduces `knowledge_architect.kir` as the canonical semantic boundary. The Core contains typed identities, entities, knowledge units, explicit relations, evidence, provenance, and canonical serialization.

```text
Source observations / future extraction
                ↓
        immutable KIR Core
                ↓
future KIR event and projection adapters
```

The KIR package is domain-only. It does not import connectors, SQLite adapters, application handlers, or projections. Existing Core objects cannot be mutated or semantically redefined by future extensions.

## Formal KIR extensions

RFC-006 adds a declarative extension boundary over the immutable KIR Core. Extensions declare versioned capabilities in reverse-domain namespaces and may depend explicitly on already registered extension versions.

```text
immutable KIR Core
        ↑ preserved unchanged
ExtensionDefinition
        ├── owned namespace
        ├── versioned capabilities
        └── explicit dependencies
                ↓
        ExtensionRegistry
```

The registry validates manifests but does not import or execute extension code. Reserved Core namespaces cannot be claimed by extensions.

## First-class knowledge transformations

RFC-007 represents semantic evolution without mutating the immutable KIR Core. Transformations record explicit source-to-target mappings, derivation provenance, and policy decisions for every relation they claim to handle.

```text
source KnowledgeUnits (preserved)
              ↓
KnowledgeUnitTransformation
    ├── new transformation identity
    ├── explicit semantic mappings
    ├── derivation provenance
    └── RelationTransformationPolicy
              ↓
new KnowledgeUnits / Relations
```

Merge and split shapes are validated, target identities must be new, and relation propagation is never implicit. A `TransformationResult` binds the transformation record to the exact immutable objects it created.

## Formal KIR validation

RFC-008 adds contextual validation for integrity rules that cannot be decided by immutable object constructors alone. Validators accumulate stable, machine-readable issues and never mutate KIR objects or registries.

```text
KIR object + ValidationContext
              ↓
      ValidationRegistry
              ↓
 one or more typed validators
              ↓
 deterministic ValidationResult
    ├── errors
    ├── warnings
    └── informational issues
```

Strict and permissive modes alter only policy-sensitive findings such as missing optional provenance or relations requiring review. Broken references and immutable Core violations remain errors in every mode. Extensions may add validators in their own scope but cannot replace or weaken Core validation.

## Storage-independent KIR queries

RFC-009 adds a declarative query boundary without introducing persistence or execution
strategy into the KIR Core.

```text
immutable Query
    ├── origin identities
    ├── predicate composition
    ├── traversal intent
    ├── ordering
    ├── projection
    └── pagination
              ↓
        QueryEngine contract
              ↓
 deterministic QueryResult
```

Queries are immutable and canonically serializable. They describe intent only. Concrete
memory, SQL, graph, RDF, or future engines implement `QueryEngine` outside the Core and
must preserve the semantics of every query component. Traversal algorithms, physical
plans, indexing, caching, and persistence are intentionally outside RFC-009.

## Persistent KIR store Port

RFC-010 introduces persistence as a Port while preserving the immutable Core and the
storage-independent query language.

```text
Application / future services
             ↓
      KnowledgeStore Port
       ├── canonical serialization
       ├── explicit conflict policy
       ├── logical transactions
       └── Query execution contract
             ↓
 InMemoryKnowledgeStore (reference adapter)
             ↓
 future database adapters
```

The Port never exposes database-specific concepts. Persisted objects retain their typed
identity, provenance, relations, evidence, and first-class transformations. The in-memory
adapter keeps deterministic identity order and evaluates RFC-009 queries without changing
the query or stored entities. SQLite, PostgreSQL, graph stores, indexing, caching, and
physical transaction optimization remain outside RFC-010.

## Storage-independent index model (RFC-011)

Indexes are disposable derived structures coordinated by `IndexManager`.
`SearchIndex` does not own entities and never becomes a source of truth. The
reference `InMemorySearchIndex` provides hash-based identity, kind, and
namespace candidate lookup.

An indexed query follows this sequence:

1. the index optionally returns candidate identities;
2. `KnowledgeStore` retrieves the authoritative entities;
3. the complete RFC-009 predicate, ordering, projection, traversal, and
   pagination semantics are applied by the Store;
4. unsupported or invalid index paths use a deterministic full scan.

Store mutations update attached indexes. If an index update fails, it is marked
invalid and query execution continues through the Store. Rebuilds consume only
`KnowledgeStore.list()`, preserving RFC-010 as the sole source of truth.

## Versioning and snapshots (RFC-012)

`knowledge_architect.kir.versioning` adds an optional historical layer over the
persistence Port. Logical identity remains `EntityId`; each immutable state is
identified by `RevisionId` and linked in a linear per-entity history. Writes use
optimistic concurrency, deletion creates a tombstone, and restoration creates a
new active revision.

`KnowledgeSnapshot` captures an immutable, deterministically ordered set of
`EntityId`/`RevisionId` references. Snapshot reconstruction resolves those exact
revisions and never depends on current state. Current-state indexes contain only
active revisions and remain derived, rebuildable structures.

## Goal Model (RFC-013)

`knowledge_architect.kir.goal` defines immutable desired knowledge states.
Goals use storage-independent Queries as success criteria and may be evaluated
against current versioned state or a specific snapshot. Goals describe what is
desired; they contain no planning, scheduling, tools or execution behavior.

## Planning Model (RFC-014)

`knowledge_architect.kir.plan` defines immutable strategies independently of execution.
Each `Plan` explicitly targets one or more Goals and contains a `PlanGraph` of first-class
`PlanStep` objects. Dependencies form a validated DAG; preconditions, postconditions, and
completion criteria may use RFC-009 Queries without executing them.

Subplans are explicit references and repository-wide validation rejects recursive cycles.
`InMemoryPlanRepository` preserves linear immutable plan revisions using RFC-012
`RevisionId` values and optimistic concurrency. Runtime state, scheduling, tools, retries,
and monitoring remain outside the KIR Planning Model.
