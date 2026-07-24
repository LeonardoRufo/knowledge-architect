from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from typing import Any, Self

import httpx

from knowledge_architect.core import SourceDocument


class NotionAPIError(RuntimeError):
    pass


class NotionClient:
    """Small read-only Notion API client.

    Raw HTTP is used deliberately so the connector is independent from SDK release cadence.
    """

    def __init__(
        self,
        token: str,
        *,
        notion_version: str = "2026-03-11",
        base_url: str = "https://api.notion.com/v1",
        timeout: float = 30.0,
    ) -> None:
        if not token.strip():
            raise ValueError("NOTION_TOKEN não foi configurado.")
        self._client = httpx.Client(
            base_url=base_url,
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {token}",
                "Notion-Version": notion_version,
                "Content-Type": "application/json",
            },
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        response = self._client.request(method, path, **kwargs)
        if response.is_error:
            try:
                detail = response.json().get("message", response.text)
            except ValueError:
                detail = response.text
            raise NotionAPIError(f"Notion API {response.status_code}: {detail}")
        return response.json()

    def search(self, query: str | None = None) -> list[dict[str, Any]]:
        body: dict[str, Any] = {"page_size": 100}
        if query:
            body["query"] = query

        results: list[dict[str, Any]] = []
        cursor: str | None = None
        while True:
            if cursor:
                body["start_cursor"] = cursor
            payload = self._request("POST", "/search", json=body)
            results.extend(payload.get("results", []))
            if not payload.get("has_more"):
                break
            cursor = payload.get("next_cursor")
            if not cursor:
                break
        return results

    def retrieve_page(self, page_id: str) -> dict[str, Any]:
        return self._request("GET", f"/pages/{page_id}")

    def iter_block_children(self, block_id: str) -> Iterator[dict[str, Any]]:
        cursor: str | None = None
        while True:
            params: dict[str, Any] = {"page_size": 100}
            if cursor:
                params["start_cursor"] = cursor
            payload = self._request("GET", f"/blocks/{block_id}/children", params=params)
            yield from payload.get("results", [])
            if not payload.get("has_more"):
                break
            cursor = payload.get("next_cursor")
            if not cursor:
                break

    def fetch_page(self, page_id: str) -> SourceDocument:
        page = self.retrieve_page(page_id)
        blocks = list(self.iter_block_children(page_id))
        title = _page_title(page) or f"Notion page {page_id}"
        markdown = "\n\n".join(filter(None, (_block_to_markdown(block) for block in blocks)))
        edited = page.get("last_edited_time")
        return SourceDocument(
            source_system="notion",
            source_id=page_id,
            title=title,
            url=page.get("url"),
            last_edited_time=datetime.fromisoformat(edited) if edited else None,
            content_markdown=markdown,
            raw_metadata={"object": page.get("object"), "archived": page.get("archived", False)},
        )


def _rich_text_plain(rich_text: list[dict[str, Any]]) -> str:
    return "".join(item.get("plain_text", "") for item in rich_text)


def _page_title(page: dict[str, Any]) -> str:
    for prop in page.get("properties", {}).values():
        if prop.get("type") == "title":
            return _rich_text_plain(prop.get("title", []))
    return ""


def _block_to_markdown(block: dict[str, Any]) -> str:
    kind = block.get("type", "")
    value = block.get(kind, {})
    text = _rich_text_plain(value.get("rich_text", []))
    if not text:
        return ""
    if kind == "heading_1":
        return f"# {text}"
    if kind == "heading_2":
        return f"## {text}"
    if kind == "heading_3":
        return f"### {text}"
    if kind == "bulleted_list_item":
        return f"- {text}"
    if kind == "numbered_list_item":
        return f"1. {text}"
    if kind == "to_do":
        mark = "x" if value.get("checked") else " "
        return f"- [{mark}] {text}"
    if kind == "quote":
        return f"> {text}"
    if kind == "code":
        language = value.get("language", "")
        return f"```{language}\n{text}\n```"
    return text
