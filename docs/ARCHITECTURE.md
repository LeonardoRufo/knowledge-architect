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
