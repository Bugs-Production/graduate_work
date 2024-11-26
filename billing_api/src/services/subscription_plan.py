from functools import lru_cache

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from db.postgres import get_session
from models.models import SubscriptionPlan
from schemas.subscription_plan import SubscriptionPlanCreate, SubscriptionPlanUpdate
from services.base import SQLAlchemyRepository


class SubscriptionPlanService(
    SQLAlchemyRepository[SubscriptionPlan, SubscriptionPlanCreate, SubscriptionPlanUpdate]
):
    def __init__(self, session: AsyncSession):
        super().__init__(model=SubscriptionPlan, session=session)


@lru_cache
def get_subscription_plan_service(
    session: AsyncSession = Depends(get_session),
) -> SubscriptionPlanService:
    return SubscriptionPlanService(session)
