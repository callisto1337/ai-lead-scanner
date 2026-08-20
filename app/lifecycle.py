import asyncio
import os
import sys
import threading
import time
import traceback

from telethon.errors import FloodWaitError  # pyright: ignore[reportMissingTypeStubs]

from app.chat_priority_worker import chat_priority_worker
from app.embedding_worker import embedding_worker
from app.message_worker import message_worker
from app.metrics import start_metrics
from app.settings import CHAT_PRIORITY_ENABLED, MESSAGE_WORKERS_COUNT
from app.types import TelegramClientProtocol
from app.watchdog import connection_watchdog


def start_embedding_worker() -> None:
    asyncio.run(embedding_worker())


def run_monitor(client: TelegramClientProtocol) -> None:
    metrics_port = int(
        os.getenv("MONITOR_METRICS_PORT", "8002")
    )

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

        for worker_id in range(
            1,
            MESSAGE_WORKERS_COUNT + 1,
        ):
            client.loop.create_task(
                message_worker(worker_id)
            )

        print(
            f"👷 Запущено message workers: {MESSAGE_WORKERS_COUNT}",
            flush=True,
        )

        client.loop.create_task(
            connection_watchdog(client)
        )

        if CHAT_PRIORITY_ENABLED:
            client.loop.create_task(
                chat_priority_worker()
            )

            print(
                "🎯 Приоритизация чатов включена",
                flush=True,
            )

        print("🖥️ Мониторинг запущен", flush=True)

        client.run_until_disconnected()

    except FloodWaitError as exc:
        handle_flood_wait(exc)

    except KeyboardInterrupt:
        print(
            "🛑 Остановка мониторинга пользователем",
            flush=True,
        )
        sys.exit(0)

    except Exception as exc:
        handle_unexpected_error(exc)


def handle_flood_wait(exc: FloodWaitError) -> None:
    wait_seconds = int(
        getattr(exc, "seconds", 3600)
    )
    wait_hours = round(wait_seconds / 3600, 2)

    print(
        (
            "⏳ Telegram ограничил повторные попытки. "
            f"FloodWait: {wait_seconds} секунд "
            f"≈ {wait_hours} часов."
        ),
        flush=True,
    )
    print(
        "🛑 Контейнер будет остановлен без немедленного перезапуска.",
        flush=True,
    )

    sys.stderr.flush()
    time.sleep(min(wait_seconds, 3600))

    sys.exit(0)


def handle_unexpected_error(exc: Exception) -> None:
    print(f"❌ Ошибка: {exc}", flush=True)
    sys.stderr.flush()

    traceback.print_exc()

    print(
        (
            "⏸️ Пауза 10 минут перед завершением, "
            "чтобы Docker не устроил быстрый цикл перезапусков."
        ),
        flush=True,
    )

    time.sleep(600)
    sys.exit(1)