# AI Lead Scanner

## Локальные адреса

- [Админка](http://localhost:8001/admin/)
- [Grafana](http://localhost:3000/)
- [Ollama](http://localhost:11434/)

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

## Запуск тест-кейсов
```shell
Clear-Host; docker compose exec monitor python -m app.prompt_test
```
Не забудь сделать свежий билд!

## Установка хука на коммит
```shell
poetry run pre-commit install
```

## Проверить код
```shell
poetry run pre-commit run --all-files
```