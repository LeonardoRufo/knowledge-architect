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
