import asyncio

from db.rabbitmq import QueueName
from workers.auth import AuthWorker
from workers.base import run_worker

if __name__ == "__main__":
    asyncio.run(run_worker(AuthWorker, QueueName.AUTH.value))
