import os

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

kir_id_to_find = "ku-integration-test"


def read_rich_text(prop: dict) -> str:
    return "".join(
        item.get("plain_text", "")
        for item in prop.get("rich_text", [])
    )


def read_title(prop: dict) -> str:
    return "".join(
        item.get("plain_text", "")
        for item in prop.get("title", [])
    )


try:
    response = notion.data_sources.query(
        data_source_id=data_source_id,
        filter={
            "property": "KIR ID",
            "rich_text": {
                "equals": kir_id_to_find,
            },
        },
    )

except APIResponseError as error:
    print("\n❌ Falha ao consultar o Notion")
    print("Código:", error.code)
    print("Mensagem:", error.message)
    raise SystemExit(1) from error


results = response.get("results", [])

if not results:
    raise RuntimeError(
        f"Nenhuma Knowledge Unit encontrada com KIR ID: {kir_id_to_find}"
    )

if len(results) > 1:
    raise RuntimeError(
        f"Foram encontradas {len(results)} páginas com o mesmo KIR ID"
    )

page = results[0]
properties = page["properties"]

unit = {
    "page_id": page["id"],
    "name": read_title(properties["Nome"]),
    "kir_id": read_rich_text(properties["KIR ID"]),
    "revision_id": read_rich_text(properties["Revision ID"]),
    "kind": (
        properties["Kind"]["select"]["name"]
        if properties["Kind"].get("select")
        else None
    ),
    "status": (
        properties["Status"]["select"]["name"]
        if properties["Status"].get("select")
        else None
    ),
    "sync_hash": read_rich_text(properties["Sync Hash"]),
    "managed_by_kir": properties["Managed by KIR"]["checkbox"],
    "source": properties["Source"].get("url"),
    "parent_ids": read_rich_text(properties["Parent IDs"]),
}

print("\n========== KNOWLEDGE UNIT ==========")

for field, value in unit.items():
    print(f"{field}: {value}")

expected = {
    "name": "Teste idempotente do Knowledge Architect",
    "kir_id": "ku-integration-test",
    "kind": "Concept",
    "status": "Draft",
    "sync_hash": "idempotency-test",
    "managed_by_kir": True,
}

differences = []

for field, expected_value in expected.items():
    actual_value = unit[field]

    if actual_value != expected_value:
        differences.append(
            {
                "field": field,
                "expected": expected_value,
                "actual": actual_value,
            }
        )

if not unit["revision_id"].startswith("rev-"):
    differences.append(
        {
            "field": "revision_id",
            "expected": "valor iniciado por rev-",
            "actual": unit["revision_id"],
        }
    )

if differences:
    print("\n⚠️ Alteração externa detectada no Notion")

    for difference in differences:
        print(f"\nCampo: {difference['field']}")
        print(f"Esperado: {difference['expected']}")
        print(f"Encontrado: {difference['actual']}")

    raise SystemExit(2)

print("\n✅ Knowledge Unit lida e validada com sucesso")