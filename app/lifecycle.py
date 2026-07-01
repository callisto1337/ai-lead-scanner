from telethon.errors import FloodWaitError
from app.metrics import start_metrics
from app.embedding_worker import embedding_worker
import sys
import time
import traceback
import threading
import asyncio


def start_embedding_worker():
    asyncio.run(embedding_worker())


def run_monitor(client):
    print("🚀 Запуск мониторинга...", flush=True)
    start_metrics()

    worker_thread = threading.Thread(
        target=start_embedding_worker,
        daemon=True
    )
    worker_thread.start()

    try:
        client.start()
        print("🖥️ Мониторинг запущен", flush=True)
        client.run_until_disconnected()

    except FloodWaitError as e:
        handle_flood_wait(e)

    except KeyboardInterrupt:
        print("🛑 Остановка мониторинга пользователем", flush=True)
        sys.exit(0)

    except Exception as e:
        handle_unexpected_error(e)


def handle_flood_wait(e: FloodWaitError):
    wait_seconds = int(getattr(e, "seconds", 3600))
    wait_hours = round(wait_seconds / 3600, 2)

    print(
        f"⏳ Telegram ограничил повторные попытки. FloodWait: {wait_seconds} секунд "
        f"≈ {wait_hours} часов.",
        flush=True,
    )
    print("🛑 Контейнер будет остановлен без немедленного перезапуска.", flush=True)

    sys.stderr.flush()
    time.sleep(min(wait_seconds, 3600))

    # Важно: exit 0, если в docker-compose стоит restart: on-failure:3
    sys.exit(0)


def handle_unexpected_error(e: Exception):
    print(f"❌ Ошибка: {e}", flush=True)
    sys.stderr.flush()

    traceback.print_exc()

    print(
        "⏸️ Пауза 10 минут перед завершением, чтобы Docker не устроил быстрый цикл перезапусков.",
        flush=True,
    )
    time.sleep(600)

    sys.exit(1)
