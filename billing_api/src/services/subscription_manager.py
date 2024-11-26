from datetime import datetime, timedelta
from functools import lru_cache
from uuid import UUID

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.postgres import get_session
from models.enums import SubscriptionStatus
from models.models import Subscription
from schemas.subscription import SubscriptionCreate, SubscriptionCreateFull, SubscriptionUpdate
from services.base import SQLAlchemyRepository
from services.exceptions import (
    AccessDeniedError,
    ActiveSubscriptionExsistsError,
    ObjectNotFoundError,
    SubscriptionCancelError,
)
from services.subscription_plan import SubscriptionPlanService


class SubscriptionManager(SQLAlchemyRepository[Subscription, SubscriptionCreateFull, SubscriptionUpdate]):
    def __init__(self, session: AsyncSession, subscription_plan_service: SubscriptionPlanService):
        super().__init__(model=Subscription, session=session)
        self._subscription_plan_service = subscription_plan_service

    async def user_has_active_subscription(self, user_id: UUID) -> bool:
        """Проверяет наличие активной подписки у пользователя.

        Считаем, что подписка является активной в том случае, если подписка оплачена и активна (active),
        либо находится в режиме ожидания оплаты (pending).

        Args:
            user_id: id пользователя, для которого проверяется наличие подписки

        Returns:
            bool: True, если у пользователя есть подписка, False в противном случае
        """
        active_statuses = [SubscriptionStatus.ACTIVE, SubscriptionStatus.PENDING]
        stmt = select(self._model).where(self._model.user_id == user_id, self._model.status.in_(active_statuses))
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def create_subscription(self, user_id: UUID, subscription_data: SubscriptionCreate) -> Subscription:
        """Создаёт новую подписку для пользователя."""
        if await self.user_has_active_subscription(user_id):
            raise ActiveSubscriptionExsistsError(f"Пользователь с id={user_id} уже имеет подписку.")

        subscription_plan = await self._subscription_plan_service.get_one_or_none(subscription_data.plan_id)
        if not subscription_plan:
            raise ObjectNotFoundError(f"План подписки с id={subscription_data.plan_id} не найден.")

        start_date = datetime.now()
        end_date = start_date + timedelta(days=subscription_plan.duration_days)

        full_subscription_data = SubscriptionCreateFull(
            user_id=user_id,
            plan_id=subscription_data.plan_id,
            start_date=start_date,
            end_date=end_date,
            status=SubscriptionStatus.PENDING,
            auto_renewal=subscription_data.auto_renewal,
        )
        return await self.create(full_subscription_data)

    async def create_payment_intent_for_subscription(self, subscription_id, *args, **kwargs):
        # TODO: инициировать платёж по подписке
        pass

    async def handle_payment_webhook_event(self, *args, **kwargs):
        # TODO: обработка ответа от платёжной системы
        pass

    async def upgrade_user_to_subscriber(self):
        pass

    async def notify_user_role_changed(self):
        pass

    async def cancel_subscription(self, user_id: UUID, subscription_id: UUID) -> Subscription:
        """Отменяет подписку пользователя."""
        # TODO: проверка, возможно ли отменить подписку (по времени)
        # TODO: возврат средств
        subscription = await self.get_one_or_none(subscription_id)
        if not subscription:
            raise ObjectNotFoundError(f"Подписка с id={subscription_id} не найдена")

        if subscription.status not in [SubscriptionStatus.ACTIVE, SubscriptionStatus.PENDING]:
            raise SubscriptionCancelError("Ошибка при попытке отмены подписки. Проверьте статус подписки.")

        if subscription.user_id != user_id:
            raise AccessDeniedError("У вас недостаточно прав для совершения этого действия")

        update_data = SubscriptionUpdate(
            status=SubscriptionStatus.CANCELLED, auto_renewal=False, end_date=datetime.now()
        )
        return await self.update(subscription_id, update_data)


@lru_cache
def get_subscription_manager(session: AsyncSession = Depends(get_session)):
    subscription_plan_service = SubscriptionPlanService(session)
    return SubscriptionManager(session=session, subscription_plan_service=subscription_plan_service)
