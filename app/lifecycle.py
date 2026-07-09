import os
import sys
import time
import traceback
import threading
import asyncio

from telethon.errors import FloodWaitError

from app.embedding_worker import embedding_worker
from app.message_worker import message_worker
from app.metrics import start_metrics


def start_embedding_worker():
    asyncio.run(embedding_worker())


def run_monitor(client):
    metrics_port = int(os.getenv("MONITOR_METRICS_PORT", "8002"))

    start_metrics(metrics_port, "Monitor")

    print(
        f"📊 Метрики запущены на: {metrics_port}/metrics",
        flush=True,
    )

    print("🚀 Запуск мониторинга...", flush=True)

    embedding_thread = threading.Thread(
        target=start_embedding_worker,
        daemon=True,
    )
    embedding_thread.start()

    try:
        client.start()

        client.loop.create_task(message_worker())

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