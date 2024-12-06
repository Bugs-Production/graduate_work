from celery import Celery, Task
from core.config import settings
from kombu import Exchange, Queue

exchange = Exchange(name="celery", type="direct")
queue = Queue(
    name="celery",
    exchange=exchange,
)

celery_app = Celery(settings.project_name, broker=settings.rabbitmq.url)

celery_app.conf.update(
    imports=["tasks.check_subscriptions"],
    broker_connection_retry_on_startup=True,
    task_track_started=True,
    beat_schedule={
        "check_subscriptons": {
            "task": "tasks.check_subscriptions.check_subscriptions",
            "schedule": settings.celery_scheduler_interval_sec,
        }
    },
    task_queues=(queue,),
)
