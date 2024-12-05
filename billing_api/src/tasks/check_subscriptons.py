from celery import shared_task

from workers.celery import queue
from asgiref.sync import async_to_sync

from models.models import Subscription
import logging
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from core.config import settings

logger = logging.getLogger()


async def main():
    engine = create_async_engine(settings.postgres_url, echo=settings.engine_echo, future=True)
    async_session = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)  # type: ignore[assignment]

    async with async_session() as session:
        pass


@shared_task(queue=queue.name)
def check_subscriptons() -> None:
    logger.info("Executing scheduled task")
    async_to_sync(main)()
    # with get_sync_session() as session:
    # stmt = select(Subscription).where(
    #     NotificationTask.status == NotificationTaskStatusEnum.INIT,
    #     NotificationTask.send_date <= time_now,
    # )
    # notifications_data = session.scalars(stmt)

    # for row in notifications_data.all():
