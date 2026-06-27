"""Importing this package registers all models on ``Base.metadata``."""

from app.models.app_state import AppState
from app.models.business import BusinessProfile
from app.models.change import Change, ChangeCategory, CrmStatus
from app.models.competitor import Competitor, MonitorScope, MonitorStatus
from app.models.snapshot import PageSnapshot
from app.models.thesis import CompetitorThesis

__all__ = [
    "AppState",
    "BusinessProfile",
    "Change",
    "ChangeCategory",
    "CrmStatus",
    "Competitor",
    "CompetitorThesis",
    "MonitorScope",
    "MonitorStatus",
    "PageSnapshot",
]
