# Онлайн-кинотеатр: Auth-сервис и интеграции

Проект собран из независимо разворачиваемых сервисов, связанных через `docker-compose.yml`. Auth-сервис интегрирован с сервисом выдачи контента и административной панелью, при этом отказ Auth-сервиса не роняет сайт: перед ним стоит прокси с прерывателем, а клиенты повторяют запросы с backoff.

Что реализовано:

- интеграция Auth-сервиса с контентным API и админкой по общему контракту, с изящной деградацией;
- трассировка запросов через заголовок `x-request-id` и отправка спанов в Jaeger;
- ограничение количества запросов к серверу — на уровне nginx и в самих приложениях;
- вход через сторонние сервисы по OAuth (реализована сторона потребителя, провайдер Яндекс; VK и Google подключаются через тот же интерфейс), включая открепление аккаунта соцсети от личного кабинета.

## Состав стека

| Сервис | Каталог | Назначение |
|---|---|---|
| `nginx` | `configs/nginx/` | Единая точка входа, **http://localhost:8080** |
| `fastapi` | `fast_api/` | Контентное API: `/api/v1/films`, `/genres`, `/persons` |
| `authapi` | `auth-service/` | Аутентификация, роли, история входов, OAuth — `/users/…` |
| `auth-circuit-breaker` | `auth-circuit-breaker/` | Прокси с прерывателем перед `authapi`; напрямую в `authapi` не ходит никто |
| `admin` | `admin/` | Django-админка, логинится через auth-сервис |
| `etl` | `etl_service/` | Перекладывает данные из Postgres в Elasticsearch |
| `jaeger` | — | Сбор трассировок, UI на http://localhost:16686 |

## Подготовка к первому запуску

### 1. Env-файлы

В git не хранятся, копируются из шаблонов:

```commandline
cp .env.example .env
cp .env.test.example .env.test
cp auth-service/.env.template auth-service/.env
cp admin/.env.example admin/.env
```

Что поправить руками:

- `auth-service/.env` — `YANDEX_CLIENT_ID` и `YANDEX_CLIENT_SECRET` из своего приложения на [oauth.yandex.ru](https://oauth.yandex.ru/), `SUPERUSER_PASSWORD`;
- `SECRET_KEY` и `ALGORITHM` должны **совпадать** в `auth-service/.env` и `admin/.env` — админка сама декодирует access-токен, выданный auth-сервисом.

### 2. OpenAPI-клиенты для админки

Каталог `admin/clients/` в git не хранится (`.gitignore`), но нужен на этапе сборки образа админки — Dockerfile просто копирует каталог целиком. Без клиентов сборка `admin` упадёт на импортах.

```commandline
cd admin
pip install openapi-python-client
openapi-python-client generate --path openapi/auth-openapi.json  --output-path clients/auth_api  --overwrite
openapi-python-client generate --path openapi/films-openapi.json --output-path clients/films_api --overwrite
```

Спецификации лежат в `admin/openapi/` и уже актуальны — перегенерировать их нужно только после изменения контрактов (см. «Генерация OpenAPI JSON»).

### 3. Запуск

```commandline
make docker
```

То же самое: `docker compose up --build`.

Миграции auth-сервиса и создание суперпользователя выполняются автоматически при старте контейнера `authapi` (`auth-service/prepare_service.sh`).

## Точки входа

| Адрес | Что там |
|---|---|
| http://localhost:8080/api/openapi | Swagger контентного API |
| http://localhost:8080/users/openapi | Swagger auth-сервиса |
| http://localhost:8080/admin/ | Django-админка |
| http://localhost:16686 | Jaeger UI |

Порт `8000` проброшен на `fastapi` напрямую — в обход nginx, для отладки.

## Локальный запуск Async API без Docker

```commandline
make run
```

Запускает `fastapi dev fast_api/main.py`. Требует уже поднятых Postgres, Elasticsearch и Redis, а переменные из `.env` должны быть **экспортированы в окружение** — настройки `fast_api` читают только `os.environ`, файл `.env` сами не подхватывают. Для обычной работы проще `make docker`.

## Запуск тестов

```commandline
make tests
```

То же самое: `docker compose -f docker-compose.test.yml up --build`.

Если нужно прогнать тесты на уже собранном образе API, сначала пересобрать его:

```commandline
make docker-api
```

Перезапустить только контейнер с тестами, не трогая поднятое окружение:

```commandline
make tests-restart
```

### Одиночный тест

Контейнер `tests` ставит зависимости в своём entrypoint, поэтому для запуска одного теста entrypoint нужно переопределить:

```commandline
docker compose -f docker-compose.test.yml up -d theatre-db elasticsearch redis fastapi authapi auth-db auth-circuit-breaker
docker compose -f docker-compose.test.yml run --rm --entrypoint sh tests -c \
  "pip install -r /tests/functional/requirements.txt && pytest /tests/functional/src/api/v1/test_film.py::test_get_film_details -q"
```

Тесты чёрного ящика: ходят в поднятые сервисы по HTTP и сами наполняют Elasticsearch. Если прогон упирается в ограничитель запросов — поднять `REQUEST_LIMIT_PER_SECOND` в `.env.test`.

## Генерация OpenAPI JSON

Поднять сервисы и скачать спецификации:

```commandline
curl http://localhost:8080/users/openapi.json > admin/openapi/auth-openapi.json
curl http://localhost:8080/api/openapi.json   > admin/openapi/films-openapi.json
```

Затем перегенерировать клиентов командами из раздела «Подготовка к первому запуску».

Имена модулей у сгенерированного клиента содержат теги роутеров, в том числе русские (`...api.пользователи.logout_users_logout_post`), — переименование тега в роутере ломает импорты в админке.

## Яндекс OAuth

- поднять сервисы;
- открыть в браузере http://localhost:8080/users/oauth/yandex/start;
- `YANDEX_REDIRECT_URI` в `auth-service/.env` должен совпадать с redirect URI, указанным в настройках приложения на стороне Яндекса (по умолчанию `http://localhost:8080/users/oauth/yandex/callback`).

Провайдеры подключаются через общий интерфейс `src/services/oauth_base.py` и реестр `src/services/oauth_registry.py`; маршруты общие — `/users/oauth/{provider_name}/start` и `/callback`, поэтому добавление VK или Google не требует правки роутов.

## Трассировка

Auth-сервис отправляет спаны в Jaeger по OTLP (`OTEL_EXPORTER_OTLP_ENDPOINT` задаётся в `docker-compose.yml`). Заголовок `x-request-id` проставляет nginx; если его нет, сервис генерирует свой и возвращает в ответе как `X-Request-Id`. Трассы — на http://localhost:16686, сервис `auth-service`.

Без `OTEL_EXPORTER_OTLP_ENDPOINT` экспорт отключается, сервис работает как обычно.

## Ограничение количества запросов

Лимиты заданы в двух местах: зоны `limit_req` в конфиге nginx на каждый location и общий пакет `shared/redis_rate_limit/` — счётчик в Redis по IP с окном в одну секунду. Пакет подключён в `fastapi` (scope `fastapi`) и в auth-сервисе (scope `auth`) через `RateLimitMiddleware`, IP берётся из заголовка `x-real-ip`, который проставляет nginx.

## Изящная деградация auth-сервиса

Перед `authapi` стоит отдельный сервис-прокси с прерывателем (circuit breaker) — параметры, состояния и политика «сбой/успех» описаны в [auth-circuit-breaker/README.md](auth-circuit-breaker/README.md). Клиенты (`fastapi`, `admin`, nginx) ходят в `auth-circuit-breaker`, а не в `authapi` напрямую; новые сервисы переиспользуют этот прерыватель, а не заводят свой.

## Линтер

```commandline
make lint                # flake8
make pre-commit-install  # хук flake8 на коммит
```
