help:
	@cat Makefile

install:
	@pip install -r requirements.txt

lint:
	@flake8

run:
	@fastapi dev fast_api/main.py

clean:
	@rm -rf .pytest_cache/ .mypy_cache/ junit/ build/ dist/
	@find . -not -path './.venv*' -path '*/__pycache__*' -delete
	@find . -not -path './.venv*' -path '*/*.egg-info*' -delete

pre-commit-install:
	@pre-commit install

test-space:
	@docker-compose -f docker-compose.test.yml up --build

docker:
	@docker compose up --build

docker-api:
	@docker compose build fastapi

tests:
	@docker-compose -f docker-compose.test.yml up tests --build

tests-restart:
	@docker-compose -f docker-compose.test.yml restart tests

openapi:
	@curl -o openapi.json http://127.0.0.1:8000/api/openapi.json

gen-clients: openapi
	# Генерация Python клиента
	docker run --rm -v ${PWD}:/local openapitools/openapi-generator-cli:v7.13.0 generate \
		-i /local/openapi.json \
		-g python \
		-o /local/clients/python \
		--additional-properties=packageName=api_client,projectName=api-python-client

	# Генерация TypeScript-Axios клиента через Docker
	docker run --rm -v ${PWD}:/local openapitools/openapi-generator-cli:v7.13.0 generate \
		-i /local/openapi.json \
		-g typescript-axios \
		-o /local/clients/ts-axios \
		--additional-properties=npmName=api-ts-client

