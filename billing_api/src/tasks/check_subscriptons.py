import logging

from celery import shared_task

from workers.celery import queue

logger = logging.getLogger()


@shared_task(queue=queue.name)
def check_subscriptons() -> None:
    logger.info("Executing scheduled task")
