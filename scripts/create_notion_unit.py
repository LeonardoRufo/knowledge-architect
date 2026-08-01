import os
from uuid import uuid4

from dotenv import load_dotenv
from notion_client import Client
from notion_client.errors import APIResponseError

load_dotenv()

token = os.getenv("NOTION_ACCESS_TOKEN")
data_source_id = os.getenv("NOTION_DATA_SOURCE_ID")

if not token:
    raise RuntimeError("NOTION_ACCESS_TOKEN não definido no .env")

if not data_source_id:
    raise RuntimeError("NOTION_DATA_SOURCE_ID não definido no .env")


notion = Client(auth=token)

kir_id = f"ku-{uuid4()}"
revision_id = f"rev-{uuid4()}"

properties = {
    "Nome": {
        "title": [
            {
                "type": "text",
                "text": {
                    "content": "Teste de integração com o Knowledge Architect"
                },
            }
        ]
    },
    "KIR ID": {
        "rich_text": [
            {
                "type": "text",
                "text": {"content": kir_id},
            }
        ]
    },
    "Revision ID": {
        "rich_text": [
            {
                "type": "text",
                "text": {"content": revision_id},
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
    "Parent IDs": {
        "rich_text": []
    },
    "Sync Hash": {
        "rich_text": [
            {
                "type": "text",
                "text": {"content": "test-sync-hash"},
            }
        ]
    },
    "Managed by KIR": {
        "checkbox": True,
    },
}

try:
    page = notion.pages.create(
        parent={
            "type": "data_source_id",
            "data_source_id": data_source_id,
        },
        properties=properties,
        children=[
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": (
                                    "Esta página foi criada automaticamente pela "
                                    "integração do Knowledge Architect."
                                )
                            },
                        }
                    ]
                },
            }
        ],
    )

except APIResponseError as error:
    print("\n❌ O Notion recusou a criação da página")
    print("Código:", error.code)
    print("Mensagem:", error.message)
    raise SystemExit(1) from error

print("\n✅ Knowledge Unit criada no Notion")
print("Page ID:", page["id"])
print("KIR ID:", kir_id)
print("Revision ID:", revision_id)
print("URL:", page.get("url", "URL não retornada"))