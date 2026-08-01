import os

from dotenv import load_dotenv
from notion_client import Client

load_dotenv()

token = os.getenv("NOTION_ACCESS_TOKEN")
database_id = os.getenv("NOTION_DATABASE_ID")

if not token:
    raise RuntimeError("NOTION_ACCESS_TOKEN não foi definido no .env")

if not database_id:
    raise RuntimeError("NOTION_DATABASE_ID não foi definido no .env")

notion = Client(auth=token)

database = notion.databases.retrieve(database_id=database_id)

print("✅ Conexão com o Notion realizada")
print("Database ID:", database["id"])

for data_source in database.get("data_sources", []):
    print(
        "Data source:",
        data_source.get("name", "sem nome"),
        "-",
        data_source["id"],
    )