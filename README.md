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