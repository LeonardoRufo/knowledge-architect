from __future__ import annotations

from typing import Any

from .models import NotionKnowledgeUnit


def _plain_text(items: list[dict[str, Any]]) -> str:
    return "".join(item.get("plain_text", "") for item in items)


def _rich_text_value(value: str) -> dict[str, Any]:
    if not value:
        return {"rich_text": []}

    return {
        "rich_text": [
            {
                "type": "text",
                "text": {
                    "content": value,
                },
            }
        ]
    }


def notion_page_to_unit(page: dict[str, Any]) -> NotionKnowledgeUnit:
    properties = page["properties"]

    kind = properties["Kind"].get("select")
    status = properties["Status"].get("select")

    parent_ids_text = _plain_text(
        properties["Parent IDs"].get("rich_text", [])
    )

    parent_ids = tuple(
        item.strip()
        for item in parent_ids_text.split(",")
        if item.strip()
    )

    return NotionKnowledgeUnit(
        page_id=page["id"],
        name=_plain_text(properties["Nome"].get("title", [])),
        kir_id=_plain_text(properties["KIR ID"].get("rich_text", [])),
        revision_id=_plain_text(
            properties["Revision ID"].get("rich_text", [])
        ),
        kind=kind["name"] if kind else "",
        status=status["name"] if status else "",
        sync_hash=_plain_text(
            properties["Sync Hash"].get("rich_text", [])
        ),
        managed_by_kir=properties["Managed by KIR"].get(
            "checkbox",
            False,
        ),
        source=properties["Source"].get("url"),
        parent_ids=parent_ids,
    )


def unit_to_notion_properties(
    unit: NotionKnowledgeUnit,
) -> dict[str, Any]:
    return {
        "Nome": {
            "title": [
                {
                    "type": "text",
                    "text": {
                        "content": unit.name,
                    },
                }
            ]
        },
        "KIR ID": _rich_text_value(unit.kir_id),
        "Revision ID": _rich_text_value(unit.revision_id),
        "Kind": {
            "select": {
                "name": unit.kind,
            }
        },
        "Status": {
            "select": {
                "name": unit.status,
            }
        },
        "Source": {
            "url": unit.source,
        },
        "Parent IDs": _rich_text_value(
            ", ".join(unit.parent_ids)
        ),
        "Sync Hash": _rich_text_value(unit.sync_hash),
        "Managed by KIR": {
            "checkbox": unit.managed_by_kir,
        },
    }