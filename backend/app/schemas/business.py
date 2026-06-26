"""Business profile request/response schemas (onboarding)."""

from pydantic import BaseModel, ConfigDict, Field


class BusinessProfileIn(BaseModel):
    product: str = Field("", description="What your product does, e.g. PM SaaS for remote teams")
    customers: str = Field("", description="Who your customers are, e.g. startups 5-50 staff")
    price_point: str = Field("", description="Your pricing, e.g. $59/mo Pro")


class BusinessProfileOut(BusinessProfileIn):
    model_config = ConfigDict(from_attributes=True)
