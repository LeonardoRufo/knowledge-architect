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
