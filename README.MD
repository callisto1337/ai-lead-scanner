# AI Lead Scanner

## Локальные адреса

- [Админка](http://localhost)

## Авторизация в телеграм по номеру
```shell
docker compose run --rm -it monitor python -m app.telegram_auth --reset
```

## Отправка ежедневного отчета в телеграм
```shell
docker compose exec bot python -m app.daily_summary
```

## Запуск проекта
```shell
docker compose up -d --build
```

## Установка хука на коммит
```shell
poetry run pre-commit install
```

## Проверить синтаксис
```shell
poetry run pre-commit run --all-files
```

## Запуск регресс-тестов
```shell
docker compose exec monitor python -m app.scripts.prompt_marking_regression_100  --niche-id 1
```
