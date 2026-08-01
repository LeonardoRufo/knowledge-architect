import os
from uuid import uuid4

from dotenv import load_dotenv
from notion_client import Client

load_dotenv()

token = os.getenv("NOTION_ACCESS_TOKEN")
data_source_id = os.getenv("NOTION_DATA_SOURCE_ID")

if not token:
    raise RuntimeError("NOTION_ACCESS_TOKEN não definido no .env")

if not data_source_id:
    raise RuntimeError("NOTION_DATA_SOURCE_ID não definido no .env")

notion = Client(auth=token)

kir_id = "ku-integration-test"
revision_id = f"rev-{uuid4()}"

result = notion.data_sources.query(
    data_source_id=data_source_id,
    filter={
        "property": "KIR ID",
        "rich_text": {
            "equals": kir_id,
        },
    },
)

properties = {
    "Nome": {
        "title": [
            {
                "type": "text",
                "text": {
                    "content": "Teste idempotente do Knowledge Architect",
                },
            }
        ]
    },
    "KIR ID": {
        "rich_text": [
            {
                "type": "text",
                "text": {
                    "content": kir_id,
                },
            }
        ]
    },
    "Revision ID": {
        "rich_text": [
            {
                "type": "text",
                "text": {
                    "content": revision_id,
                },
            }
        ]
    },
    "Kind": {
        "select": {
            "name": "Concept",
        }
    },
    "Status": {
        "select": {
            "name": "Draft",
        }
    },
    "Sync Hash": {
        "rich_text": [
            {
                "type": "text",
                "text": {
                    "content": "idempotency-test",
                },
            }
        ]
    },
    "Managed by KIR": {
        "checkbox": True,
    },
}

if result["results"]:
    page_id = result["results"][0]["id"]

    notion.pages.update(
        page_id=page_id,
        properties=properties,
    )

    print("✅ Knowledge Unit existente atualizada")
    print("Page ID:", page_id)

else:
    page = notion.pages.create(
        parent={
            "type": "data_source_id",
            "data_source_id": data_source_id,
        },
        properties=properties,
    )

    print("✅ Nova Knowledge Unit criada")
    print("Page ID:", page["id"])

print("KIR ID:", kir_id)
print("Revision ID:", revision_id)