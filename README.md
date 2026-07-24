# Knowledge Architect

Primeiro repositório modular do **Knowledge Architect Agent (KAA)**. Esta entrega contém um núcleo event-sourced, materialização determinística e um conector **somente leitura** para o Notion.

## O que já funciona

- autenticação por token de conexão interna do Notion;
- descoberta das páginas compartilhadas com a conexão;
- leitura de propriedades e blocos de uma página;
- conversão básica dos blocos para Markdown;
- emissão de eventos imutáveis;
- armazenamento local em SQLite;
- materialização e exportação do estado atual;
- testes automatizados sem depender de uma conta real.

## Instalação

### macOS / Linux

```bash
cd knowledge-architect
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
cp .env.example .env
```

### Windows PowerShell

```powershell
cd knowledge-architect
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Abra `.env` e substitua apenas o valor de `NOTION_TOKEN`. Não compartilhe nem faça commit desse arquivo.

## Compartilhar uma página com a conexão

No Notion, abra a página desejada e use **••• → Conexões → Knowledge Architect**. A API só consegue descobrir conteúdo explicitamente compartilhado com a conexão.

## Primeiro teste

```bash
kaa notion status
kaa notion list
```

Copie o ID de uma página exibida e execute:

```bash
kaa notion sync-page ID_DA_PAGINA
kaa status
kaa export data/architecture.json
```

## Estrutura

```text
knowledge-architect/
├── src/knowledge_architect/
│   ├── application/
│   ├── core/
│   ├── connectors/notion/
│   ├── event_store/
│   ├── materializer/
│   └── cli.py
├── tests/
├── docs/
│   ├── adr/
│   ├── rfc/
│   └── specification/
├── data/
├── .env.example
└── pyproject.toml
```

## Limites desta versão

- sincroniza uma página por comando;
- converte apenas os blocos textuais mais comuns;
- ainda não extrai conceitos, relações ou Knowledge Units;
- não escreve nada no Notion;
- não executa LLM nem decisões autônomas.

O próximo marco será sincronização incremental de várias páginas, seguida pela camada de extração semântica revisável.
