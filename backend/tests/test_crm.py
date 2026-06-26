"""CRM idempotency — pushing the same change twice must not duplicate it.

Uses a fake Notion client (an in-memory store) so the idempotency contract is
verified with no live token or network.
"""

import uuid
from datetime import UTC, datetime

from app.models.change import Change, ChangeCategory, CrmStatus
from app.models.competitor import Competitor
from app.services import crm


class _FakeDatabases:
    def __init__(self, store: list):
        self.store = store

    async def query(self, *, database_id, filter):  # noqa: A002 — mirror Notion's kwarg name
        wanted = filter["rich_text"]["equals"]
        return {"results": [p for p in self.store if p["argus_id"] == wanted]}


class _FakePages:
    def __init__(self, store: list):
        self.store = store
        self.create_calls = 0

    async def create(self, *, parent, properties):
        self.create_calls += 1
        argus_id = properties["Argus ID"]["rich_text"][0]["text"]["content"]
        page = {"id": f"page-{argus_id}", "argus_id": argus_id}
        self.store.append(page)
        return page


class _FakeNotion:
    def __init__(self):
        self.store: list = []
        self.pages = _FakePages(self.store)
        self.databases = _FakeDatabases(self.store)


def _make_change() -> Change:
    change = Change(
        id=uuid.uuid4(),
        competitor_id=uuid.uuid4(),
        to_snapshot_id=uuid.uuid4(),
        is_meaningful=True,
        category=ChangeCategory.pricing,
        summary="Acme cut prices",
        impact_score=6,
        recommended_action="Review pricing",
        crm_status=CrmStatus.pending,
    )
    change.detected_at = datetime.now(UTC)  # normally a server default
    return change


async def test_crm_push_is_idempotent():
    fake = _FakeNotion()
    competitor = Competitor(id=uuid.uuid4(), name="Acme", url="https://acme.example")
    change = _make_change()

    page_id_1, created_1 = await crm.sync_change(fake, "db-id", change, competitor)
    page_id_2, created_2 = await crm.sync_change(fake, "db-id", change, competitor)

    assert created_1 is True       # first push creates
    assert created_2 is False      # second push finds the existing page
    assert page_id_1 == page_id_2  # same Notion page
    assert fake.pages.create_calls == 1  # exactly one record ever created
