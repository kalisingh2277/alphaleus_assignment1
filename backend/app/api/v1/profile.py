"""Business profile endpoints (onboarding / settings)."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.business import SINGLETON_ID, BusinessProfile
from app.schemas.business import BusinessProfileIn, BusinessProfileOut

router = APIRouter(prefix="/profile", tags=["profile"])


async def _get_or_create(session: AsyncSession) -> BusinessProfile:
    profile = await session.get(BusinessProfile, SINGLETON_ID)
    if profile is None:
        profile = BusinessProfile(id=SINGLETON_ID)
        session.add(profile)
        await session.commit()
        await session.refresh(profile)
    return profile


@router.get("", response_model=BusinessProfileOut)
async def get_profile(session: AsyncSession = Depends(get_session)) -> BusinessProfile:
    return await _get_or_create(session)


@router.put("", response_model=BusinessProfileOut)
async def update_profile(
    payload: BusinessProfileIn, session: AsyncSession = Depends(get_session)
) -> BusinessProfile:
    profile = await _get_or_create(session)
    profile.product = payload.product
    profile.customers = payload.customers
    profile.price_point = payload.price_point
    await session.commit()
    await session.refresh(profile)
    return profile
