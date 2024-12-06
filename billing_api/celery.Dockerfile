FROM python:3.11

WORKDIR /opt/app

COPY . .

RUN apt-get update \
    && pip install --no-cache-dir poetry \
    && poetry config virtualenvs.create false \
    && poetry install --only main --no-interaction --no-ansi --no-root \
    && rm -rf ~/.cache

WORKDIR /opt/app/src

CMD ["celery", "-A", "workers.celery.celery_app", "worker", "--loglevel=info"]
