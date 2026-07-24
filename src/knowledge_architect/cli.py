from __future__ import annotations

import json
from pathlib import Path

import typer

from knowledge_architect.connectors.notion import NotionClient, NotionConnector
from knowledge_architect.event_store import SQLiteEventStore
from knowledge_architect.materializer import materialize
from knowledge_architect.settings import Settings

app = typer.Typer(help="Knowledge Architect Agent")
notion_app = typer.Typer(help="Conector read-only do Notion")
app.add_typer(notion_app, name="notion")


@notion_app.command("status")
def notion_status() -> None:
    """Verifica autenticação e mostra quantos objetos são visíveis à conexão."""
    settings = Settings.from_env()
    with NotionClient(settings.notion_token, notion_version=settings.notion_version) as client:
        results = client.search()
    pages = sum(1 for item in results if item.get("object") == "page")
    typer.echo(json.dumps({"ok": True, "objects": len(results), "pages": pages}, indent=2))


@notion_app.command("list")
def notion_list(query: str | None = typer.Option(None, help="Filtro textual opcional")) -> None:
    """Lista páginas e fontes de dados compartilhadas com a conexão."""
    settings = Settings.from_env()
    with NotionClient(settings.notion_token, notion_version=settings.notion_version) as client:
        results = client.search(query)
    for item in results:
        typer.echo(f"{item.get('object', '?'):12} {item.get('id')}  {item.get('url', '')}")


@notion_app.command("sync-page")
def notion_sync_page(page_id: str) -> None:
    """Importa uma página do Notion como evento imutável."""
    settings = Settings.from_env()
    store = SQLiteEventStore(settings.store_path)
    with NotionClient(settings.notion_token, notion_version=settings.notion_version) as client:
        connector = NotionConnector(client)
        document = connector.fetch(page_id)
        inserted = store.append([connector.to_event(document)])
    typer.echo(json.dumps({"inserted": inserted, "title": document.title}, ensure_ascii=False))


@app.command("status")
def status() -> None:
    """Mostra o estado local do KAA."""
    settings = Settings.from_env()
    store = SQLiteEventStore(settings.store_path)
    state = materialize(store.list_events())
    typer.echo(json.dumps({"events": store.count(), **state["statistics"]}, indent=2))


@app.command("export")
def export(output: Path = typer.Argument(Path("data/architecture.json"))) -> None:
    """Materializa e exporta o estado atual."""
    settings = Settings.from_env()
    store = SQLiteEventStore(settings.store_path)
    state = materialize(store.list_events())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    typer.echo(str(output))


if __name__ == "__main__":
    app()
