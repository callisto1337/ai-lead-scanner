# AI Lead Scanner

## Авторизация в телеграм по номеру
```shell
docker compose run --rm -it monitor python -m app.telegram_auth --reset
```

## Запуск проекта
```shell
docker compose up -d --build
```

## Запуск тестов
```shell
Clear-Host; docker compose exec monitor python -m app.prompt_test
```
Не забудь сделать свежий билд!

## Локальные адреса

- [Админка](http://localhost:8001/admin/)
- [Grafana](http://localhost:3000/)
- [Ollama](http://localhost:11434/)
