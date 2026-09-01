# Проектная работа спринта

1. Создайте интеграцию Auth-сервиса с сервисом выдачи контента и административной панелью, используя контракт, который вы сделали в прошлом задании.

    При создании интеграции не забудьте учесть изящную деградацию Auth-сервиса. Auth сервис — один из самых нагруженных, потому что в него ходят большинство сервисов сайта. И если он откажет, сайт отказать не должен. Обязательно учтите этот сценарий в интеграциях с Auth-сервисом.
2. Добавьте в Auth-сервис трассировку и подключите к Jaeger. Для этого вам нужно добавить работу с заголовком x-request-id и отправку трассировок в Jaeger.
3. Добавьте в сервис механизм ограничения количества запросов к серверу.
4. Упростите регистрацию и аутентификацию пользователей в Auth-сервисе, добавив вход через социальные сервисы. Список сервисов выбирайте исходя из целевой аудитории онлайн-кинотеатра — подумайте, какими социальными сервисами они пользуются. Например, использовать [OAuth от Github](https://docs.github.com/en/free-pro-team@latest/developers/apps/authorizing-oauth-apps){target="_blank"} — не самая удачная идея. Ваши пользователи — не разработчики и вряд ли пользуются аккаунтом на Github. Лучше добавить Yandex, VK или Google.

    Вам не нужно делать фронтенд в этой задаче и реализовывать собственный сервер OAuth. Нужно реализовать протокол со стороны потребителя.

    Информация по OAuth у разных поставщиков данных:

    - [Yandex](https://yandex.ru/dev/oauth/?turbo=true){target="_blank"},
    - [VK](https://vk.com/dev/access_token){target="_blank"},
    - [Google](https://developers.google.com/identity/protocols/oauth2){target="_blank"}.
5. Партицируйте таблицу с пользователями или с историей входов. Подумайте, по каким критериям вы бы разделили её. Важно посмотреть на таблицу не только в текущем времени, но и заглядывая в некое будущее, когда в ней будут миллионы записей. Пользователи могут быть из одной страны, но из разных регионов. А ещё пользователи могут использовать разные устройства для входа и иметь разные возрастные ограничения.

## Дополнительное задание

Реализуйте возможность открепить аккаунт в соцсети от личного кабинета.

Решение залейте в репозиторий текущего спринта и отправьте на ревью.

---

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

Для генерации клиентов на других языках через `openapi-generator` есть `make gen-clients` (Python и TypeScript-Axios, спецификация берётся с `127.0.0.1:8000`).

## Яндекс OAuth

- поднять сервисы;
- открыть в браузере http://localhost:8080/users/oauth/yandex/start;
- `YANDEX_REDIRECT_URI` в `auth-service/.env` должен совпадать с redirect URI, указанным в настройках приложения на стороне Яндекса (по умолчанию `http://localhost:8080/users/oauth/yandex/callback`).

Провайдеры подключаются через общий интерфейс `src/services/oauth_base.py` и реестр `src/services/oauth_registry.py`; маршруты общие — `/users/oauth/{provider_name}/start` и `/callback`, поэтому добавление VK или Google не требует правки роутов.

## Трассировка

Auth-сервис отправляет спаны в Jaeger по OTLP (`OTEL_EXPORTER_OTLP_ENDPOINT` задаётся в `docker-compose.yml`). Заголовок `x-request-id` проставляет nginx; если его нет, сервис генерирует свой и возвращает в ответе как `X-Request-Id`. Трассы — на http://localhost:16686, сервис `auth-service`.

Без `OTEL_EXPORTER_OTLP_ENDPOINT` экспорт отключается, сервис работает как обычно.

## Изящная деградация auth-сервиса

Перед `authapi` стоит отдельный сервис-прокси с прерывателем (circuit breaker) — параметры, состояния и политика «сбой/успех» описаны в [auth-circuit-breaker/README.md](auth-circuit-breaker/README.md). Клиенты (`fastapi`, `admin`, nginx) ходят в `auth-circuit-breaker`, а не в `authapi` напрямую; новые сервисы должны переиспользовать этот прерыватель, а не заводить свой.

## Линтер

```commandline
make lint                # flake8
make pre-commit-install  # хук flake8 на коммит
```
