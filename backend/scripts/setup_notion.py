"""One-time helper: create the Argus Notion database with the correct schema.

Setup once, then paste the printed id into NOTION_DATABASE_ID.

    1. Create an internal integration at https://www.notion.so/my-integrations
       and copy its secret (starts with "ntn_" / "secret_").
    2. Create a Notion page, and in its ... menu → Connections, add your integration.
    3. Copy that page's id from its URL (the 32-char hex after the title).
    4. Run:
         NOTION_TOKEN=ntn_xxx NOTION_PARENT_PAGE_ID=<page-id> \
           uv run python scripts/setup_notion.py
"""

import asyncio
import os

from notion_client import AsyncClient

_CATEGORIES = ["pricing", "product", "hiring", "messaging", "leadership", "other"]


async def main() -> None:
    token = os.environ["NOTION_TOKEN"]
    parent_page_id = os.environ["NOTION_PARENT_PAGE_ID"]
    client = AsyncClient(auth=token)

    db = await client.databases.create(
        parent={"type": "page_id", "page_id": parent_page_id},
        title=[{"type": "text", "text": {"content": "Argus — Competitor Intelligence"}}],
        properties={
            "Name": {"title": {}},
            "Competitor": {"rich_text": {}},
            "URL": {"url": {}},
            "Category": {"select": {"options": [{"name": c} for c in _CATEGORIES]}},
            "Impact Score": {"number": {}},
            "Summary": {"rich_text": {}},
            "Recommended Action": {"rich_text": {}},
            "Detected At": {"date": {}},
            "Argus ID": {"rich_text": {}},
        },
    )
    print("Created database. Set this in your .env:")
    print(f"NOTION_DATABASE_ID={db['id']}")


if __name__ == "__main__":
    asyncio.run(main())
