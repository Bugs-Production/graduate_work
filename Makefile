.PHONY: build
build:
	docker compose build

.PHONY: start
start:
	docker compose up -d --build

.PHONY: stop
stop:
	docker compose down

.PHONY: format
format:
	ruff check . --output-format=full --fix
	ruff format .
	mypy . --follow-imports=skip

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
