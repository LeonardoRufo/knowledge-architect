import os

from dotenv import load_dotenv
from notion_client import Client

load_dotenv()

token = os.getenv("NOTION_ACCESS_TOKEN")
data_source_id = os.getenv("NOTION_DATA_SOURCE_ID")

if not token:
    raise RuntimeError("NOTION_ACCESS_TOKEN não definido")

if not data_source_id:
    raise RuntimeError("NOTION_DATA_SOURCE_ID não definido")

notion = Client(auth=token)

data_source = notion.data_sources.retrieve(
    data_source_id=data_source_id,
)

print("\n========== DATA SOURCE ==========")
print("Nome:", data_source.get("name", "sem nome"))
print("ID:", data_source["id"])

print("\n========== PROPRIEDADES ==========")

for property_name, property_data in data_source.get("properties", {}).items():
    print(
        f"- {property_name}: "
        f"{property_data.get('type', 'tipo desconhecido')}"
    )