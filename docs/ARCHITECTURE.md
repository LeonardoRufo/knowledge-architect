# Arquitetura 0.1

```text
Notion (interface humana)
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

## Fronteiras

- **TKA:** princípios teóricos; não depende de tecnologia.
- **KIR:** representação canônica futura do estado semântico.
- **KAS:** contratos operacionais e transformações.
- **KAE/KAA:** implementação executável e agente.
- **Connectors:** traduz fontes externas para documentos e eventos; não definem a semântica do Core.

## Segurança

A versão 0.1 exige apenas `Ler conteúdo`. Atualização, inserção, comentários e dados de usuários não são necessários.
