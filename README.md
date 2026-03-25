## Запуск Async API
```commandline
make run
```

## Запуск БД авторизации
```commandline
cd auth-service
make auth-db
```

## Запуск тестов
```commandline
docker-compose -f docker-compose.test.yml up --build
```

### Если нужно тестировать тот же образ
Сначала:
```commandline
docker-compose build fastapi
```
Далее запуск тестового контейнера.

## Генерация Open API JSON сервиса
- запустить нужный сервис
- перейти в корень сервиса, которому нужен клиент
- скачать JSON
```
curl http://localhost/{рутер сервиса}/openapi.json > openapi-auth.json
```
- здесь же установить openapi-python-client
- выполнить
```
openapi-python-client generate \                            
  --path openapi-auth.json \
  --output-path clients/auth_api \
--overwrite
```
- если выдаст ошибку "директория clients не найдена", создать её руками
