"""One-time helper: create the Argus Notion database with the correct schema.

Fill NOTION_TOKEN and NOTION_PARENT_PAGE_ID in backend/.env, then run:

    uv run python scripts/setup_notion.py

It prints the NOTION_DATABASE_ID to paste back into .env.

Notion's current API splits a database into a "data source" that holds the rows
and their schema, so we create the database, then set the properties on its data
source.

Where to get the inputs:
  1. Create an internal integration at https://www.notion.so/my-integrations
     and copy its secret (starts with "ntn_").
  2. Create a Notion page, open its ... menu -> Connections, add your integration.
  3. Copy that page's id: the 32-hex-char string in its URL.
"""

import asyncio
import os
import sys

from dotenv import load_dotenv
from notion_client import AsyncClient

_CATEGORIES = ["pricing", "product", "hiring", "messaging", "leadership", "other"]

_PROPERTIES = {
    "Name": {"title": {}},
    "Competitor": {"rich_text": {}},
    "URL": {"url": {}},
    "Category": {"select": {"options": [{"name": c} for c in _CATEGORIES]}},
    "Impact Score": {"number": {}},
    "Summary": {"rich_text": {}},
    "Recommended Action": {"rich_text": {}},
    "Detected At": {"date": {}},
    "Argus ID": {"rich_text": {}},
}


async def main() -> None:
    load_dotenv()  # reads backend/.env when run from the backend dir
    token = os.getenv("NOTION_TOKEN")
    parent_page_id = os.getenv("NOTION_PARENT_PAGE_ID")
    if not token or not parent_page_id:
        sys.exit("Set NOTION_TOKEN and NOTION_PARENT_PAGE_ID in backend/.env first.")

    client = AsyncClient(auth=token)
    db = await client.databases.create(
        parent={"type": "page_id", "page_id": parent_page_id},
        title=[{"type": "text", "text": {"content": "Argus — Competitor Intelligence"}}],
    )
    data_source_id = db["data_sources"][0]["id"]
    await client.data_sources.update(data_source_id=data_source_id, properties=_PROPERTIES)

    print("Created the database. Paste this into backend/.env:")
    print(f"NOTION_DATABASE_ID={db['id']}")


if __name__ == "__main__":
    asyncio.run(main())
