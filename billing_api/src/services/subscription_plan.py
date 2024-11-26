from functools import lru_cache
from uuid import UUID

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.postgres import get_session
from models.models import SubscriptionPlan
from schemas.subscription_plan import SubscriptionPlanCreate, SubscriptionPlanUpdate
from services.base import SQLAlchemyRepository
from services.exceptions import ObjectAlreadyExistsError


class SubscriptionPlanService(SQLAlchemyRepository[SubscriptionPlan, SubscriptionPlanCreate, SubscriptionPlanUpdate]):
    def __init__(self, session: AsyncSession):
        super().__init__(model=SubscriptionPlan, session=session)

    async def check_subscription_plan_exists_by_title(self, title: str) -> bool:
        stmt = select(self._model).where(self._model.title == title)
        existing_plan = await self._session.execute(stmt)
        return existing_plan.scalar_one_or_none() is not None

    async def create_new_subscription_plan(self, subscription_plan_data: SubscriptionPlanCreate) -> SubscriptionPlan:
        if await self.check_subscription_plan_exists_by_title(subscription_plan_data.title):
            raise ObjectAlreadyExistsError("План подписки с выбранным заголовком уже существует.")
        return await self.create(subscription_plan_data)

    async def update_subscription_plan(
        self, subscription_plan_id: UUID, subscription_plan_data: SubscriptionPlanUpdate
    ) -> SubscriptionPlan:
        if subscription_plan_data.title is None:
            return await self.update(subscription_plan_id, subscription_plan_data)
        if await self.check_subscription_plan_exists_by_title(subscription_plan_data.title):
            raise ObjectAlreadyExistsError("План подписки с выбранным заголовком уже существует.")
        return await self.update(subscription_plan_id, subscription_plan_data)


@lru_cache
def get_subscription_plan_service(
    session: AsyncSession = Depends(get_session),
) -> SubscriptionPlanService:
    return SubscriptionPlanService(session)
