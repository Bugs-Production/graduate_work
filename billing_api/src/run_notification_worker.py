import asyncio

from db.rabbitmq import QueueName
from workers.base import run_worker
from workers.notification import NotificationWorker

if __name__ == "__main__":
    asyncio.run(run_worker(NotificationWorker, QueueName.NOTIFICATION.value))
