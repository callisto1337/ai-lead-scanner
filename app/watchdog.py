import asyncio
import time

from telegram import Bot

from app.daily_summary import send_message_with_retry
from app.settings import (
    BOT_ADMIN_IDS,
    BOT_TOKEN,
    MONITOR_STALE_THRESHOLD_SECONDS,
    MONITOR_WATCHDOG_INTERVAL_SECONDS,
)
from app.types import TelegramClientProtocol

RECONNECT_RETRY_SECONDS = 300
ALERT_GRACE_SECONDS = 180

_last_event_at = time.monotonic()
_notified = False
_last_reconnect_attempt: float | None = None


def mark_event_received() -> None:
    global _last_event_at
    _last_event_at = time.monotonic()


async def _notify_admins(text: str) -> None:
    if not BOT_ADMIN_IDS:
        return

    bot = Bot(BOT_TOKEN)

    for admin_id in BOT_ADMIN_IDS:
        try:
            await send_message_with_retry(
                bot=bot,
                chat_id=admin_id,
                text=text,
            )

        except Exception as error:
            print(
                f"❌ Не удалось уведомить админа {admin_id}: {error}",
                flush=True,
            )


async def connection_watchdog(
    client: TelegramClientProtocol,
) -> None:
    global _notified, _last_reconnect_attempt

    print("🐕 Watchdog мониторинга запущен", flush=True)

    while True:
        await asyncio.sleep(MONITOR_WATCHDOG_INTERVAL_SECONDS)

        now = time.monotonic()
        idle_seconds = now - _last_event_at

        if idle_seconds < MONITOR_STALE_THRESHOLD_SECONDS:
            _last_reconnect_attempt = None

            if _notified:
                _notified = False

                print("✅ Мониторинг снова получает сообщения", flush=True)

                await _notify_admins(
                    "✅ Мониторинг лидов снова получает сообщения из Telegram."
                )

            continue

        if (
            _last_reconnect_attempt is None
            or now - _last_reconnect_attempt >= RECONNECT_RETRY_SECONDS
        ):
            print(
                (
                    f"⚠️ Нет новых сообщений {int(idle_seconds // 60)} мин, "
                    "пробуем переподключиться"
                ),
                flush=True,
            )

            try:
                await client.disconnect()
                await client.connect()

                print("🔄 Переподключение выполнено", flush=True)

            except Exception as error:
                print(f"❌ Ошибка переподключения: {error}", flush=True)

            _last_reconnect_attempt = now

        incident_age = idle_seconds - MONITOR_STALE_THRESHOLD_SECONDS

        if incident_age >= ALERT_GRACE_SECONDS and not _notified:
            _notified = True

            print("🚨 Простой не устранён, уведомляем админов", flush=True)

            await _notify_admins(
                "🚨 Мониторинг лидов не получает сообщения из Telegram уже "
                f"{int(idle_seconds // 60)} мин. Автоматическое "
                "переподключение не помогло, нужна ручная проверка."
            )
