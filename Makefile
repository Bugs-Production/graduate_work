.PHONY: build
build:
	docker compose --env-file billing_api/src/.env build

.PHONY: start
start:
	docker compose --env-file billing_api/src/.env up -d

.PHONY: stop
stop:
	docker compose --env-file billing_api/src/.env down

.PHONY: format
format:
	cd billing_api/src ; mypy --follow-imports=skip .
	ruff format .
	ruff check . --output-format=full --fix

.PHONY: makemigrations
makemigrations:
	@read -p "Enter migration message: " MSG; \
	docker exec billing_api alembic revision --autogenerate -m "$$MSG"

.PHONY: migrate
migrate:
	docker exec billing_api alembic upgrade head

.PHONY: downgrade
downgrade:
	@read -p "Enter revision number: " MSG; \
	 docker exec billing_api alembic downgrade "$$MSG"

.PHONY: tests
tests:
	cd billing_api/src ; pytest -v -s

#.PHONY: up_test_db
#up_test_db:
#	cd billing_api/src/tests ; docker compose up -d

.PHONY: start_rabbit
start_rabbit:
	docker run -d --name rabbitmq -p 15672:15672 -p 5672:5672 -e RABBITMQ_DEFAULT_USER=user -e RABBITMQ_DEFAULT_PASS=password rabbitmq:4.0.4-management
