from datetime import datetime, timedelta
from functools import lru_cache
from uuid import UUID

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.postgres import get_session
from models.enums import SubscriptionStatus
from models.models import Subscription
from schemas.subscription import SubscriptionCreate, SubscriptionCreateFull, SubscriptionRenew, SubscriptionUpdate
from services.base import SQLAlchemyRepository
from services.exceptions import AccessDeniedError, ActiveSubscriptionExsistsError, SubscriptionCancelError
from services.subscription_plan import SubscriptionPlanService


class SubscriptionService(SQLAlchemyRepository[Subscription, SubscriptionCreateFull, SubscriptionUpdate]):
    def __init__(
        self,
        session: AsyncSession,
        subscription_plan_service: SubscriptionPlanService,
    ):
        super().__init__(model=Subscription, session=session)
        self._subscription_plan_service = subscription_plan_service

    async def create_subscription(self, user_id: UUID, subscription_data: SubscriptionCreate) -> Subscription:
        """Создаёт новую подписку для пользователя."""
        if await self._user_has_active_subscription(user_id):
            raise ActiveSubscriptionExsistsError(f"Пользователь с id={user_id} уже имеет подписку.")

        subscription_plan = await self._subscription_plan_service.get(subscription_data.plan_id)

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

    async def cancel_subscription(self, user_id: UUID, subscription_id: UUID) -> Subscription:
        """Отменяет подписку пользователя."""
        subscription = await self._validate_subscription_access(user_id, subscription_id)

        if subscription.status not in [SubscriptionStatus.ACTIVE, SubscriptionStatus.PENDING]:
            raise SubscriptionCancelError("Ошибка при попытке отмены подписки. Проверьте статус подписки.")

        update_data = SubscriptionUpdate(
            status=SubscriptionStatus.CANCELLED, auto_renewal=False, end_date=datetime.now()
        )
        result = await self.update(subscription_id, update_data)
        return result

    async def toggle_auto_renewal(self, user_id: UUID, subscription_id: UUID) -> Subscription:
        """Переключает режим автоматического продления подписки.

        Если автоматическое продление включено - отключает его и наоборот.
        """
        subscription = await self._validate_subscription_access(user_id, subscription_id)
        new_auto_renewal = not subscription.auto_renewal
        update_data = SubscriptionUpdate(auto_renewal=new_auto_renewal)
        return await self.update(subscription.id, update_data)

    async def renew_subscription(
        self, user_id: UUID, subscription_id: UUID, renew_data: SubscriptionRenew
    ) -> Subscription:
        """Продляет подписку.

        Под продлением понимается смещение даты завершения подписки на количество дней, указанных в плане подписки.
        """
        subscription_plan = await self._subscription_plan_service.get(renew_data.plan_id)
        subscription = await self._validate_subscription_access(user_id, subscription_id)
        new_end_date = subscription.end_date + timedelta(days=subscription_plan.duration_days)
        update_data = SubscriptionUpdate(end_date=new_end_date)
        return await self.update(subscription.id, update_data)

    async def change_status(self, subscription_id: UUID, new_status: SubscriptionStatus) -> Subscription:
        """Обновляет статус подписки."""
        subscription = await self.get(subscription_id)
        update_data = SubscriptionUpdate(status=new_status)
        return await self.update(subscription.id, update_data)

    async def get_user_subscription(self, user_id: UUID, subscription_id: UUID) -> Subscription:
        return await self._validate_subscription_access(user_id, subscription_id)

    async def _user_has_active_subscription(self, user_id: UUID) -> bool:
        """Проверяет наличие активной подписки у пользователя.

        Считаем, что подписка является активной в том случае, если подписка оплачена и активна (active),
        либо находится в режиме ожидания оплаты (pending).
        """
        active_statuses = [SubscriptionStatus.ACTIVE, SubscriptionStatus.PENDING]
        stmt = select(self._model).where(self._model.user_id == user_id, self._model.status.in_(active_statuses))
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def _validate_subscription_access(self, user_id: UUID, subscription_id: UUID) -> Subscription:
        """Проверяет, что подписка с указанным subscription_id существует и редактирование подписки доступно
        пользователю с указанным user_id."""
        subscription = await self.get(subscription_id)
        if subscription.user_id != user_id:
            raise AccessDeniedError("У вас недостаточно прав для совершения этого действия")
        return subscription


@lru_cache
def get_subscription_service(session: AsyncSession = Depends(get_session)) -> Subscription:
    subscription_plan_service = SubscriptionPlanService(session)
    return Subscription(session=session, subscription_plan_service=subscription_plan_service)
