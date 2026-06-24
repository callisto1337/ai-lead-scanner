import asyncio
import httpx
from datetime import datetime, timezone, timedelta
from telegram import Bot
from settings import (
    PROMETHEUS_URL,
    BOT_TOKEN,
    CHAT_ID,
    METRICS_TOPIC_ID,
)

PROM_QUERY_TEMPLATE = 'increase({metric}[24h])'


def _parse_prometheus_increase(resp_json) -> int:
    try:
        if resp_json.get("status") != "success":
            return 0

        data = resp_json.get("data", {})
        result = data.get("result", [])
        if not result:
            return 0

        # Result is a list of vectors; takes first value.
        # value is [timestamp, value]
        value = result[0].get("value", [None, "0"])[1]
        return int(float(value))
    except Exception as e:
        print(f"❌ Ошибка при парсинге Prometheus ответа: {e}. Ответ: {resp_json}", flush=True)
        return 0


def query_prometheus(metric_name: str) -> int:
    url = PROMETHEUS_URL.rstrip("/") + "/api/v1/query"
    query = PROM_QUERY_TEMPLATE.format(metric=metric_name)

    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.get(url, params={"query": query})
            r.raise_for_status()
            return _parse_prometheus_increase(r.json())
    except Exception as e:
        print(f"❌ Ошибка при запросе к Prometheus ({url}). Метрика: {metric_name}. Ошибка: {e}", flush=True)
        return 0


def build_summary() -> dict:
    """Возвращает статистику за последние 24 часа, беря данные из Prometheus."""
    print("🔍 Начинаю запрос к Prometheus...", flush=True)
    keys = {
        "messages": "messages_total",
        "spam": "spam_total",
        "leads": "leads_total",
        "ai_requests": "ai_requests_total",
        "leads_approved": "leads_approved_total",
        "leads_rejected": "leads_rejected_total",
        "leads_skipped": "leads_skipped_total",
        "leads_blocked": "leads_blocked_total",
    }

    data = {k: query_prometheus(v) for k, v in keys.items()}
    print(f"✅ Получены данные из Prometheus: {data}", flush=True)
    data["ts"] = datetime.now(tz=timezone(timedelta(hours=3))).strftime("%d.%m.%Y %H:%M")
    return data


async def send_summary_message():
    stats = build_summary()

    text = (
        f"📋 Сводка за последние 24 часа (МСК)\n\n"
        f"Всего сообщений: {stats['messages']}\n"
        f"Спам (фильтрация): {stats['spam']}\n"
        f"Запросов к AI: {stats['ai_requests']}\n"
        f"Обнаружено лидов: {stats['leads']}\n\n"
        f"Одобренных лидов: {stats['leads_approved']}\n"
        f"Отклоненных лидов: {stats['leads_rejected']}\n"
        f"Пропущенных лидов: {stats['leads_skipped']}\n"
        f"Заблокированных лидов: {stats['leads_blocked']}\n\n"
        f"Дата отчета: {stats['ts']}")


    bot = Bot(BOT_TOKEN)

    for attempt in range(3):
        try:
            await bot.send_message(
                chat_id=CHAT_ID,
                text=text,
                message_thread_id=METRICS_TOPIC_ID,
            )
            return
        except Exception:
            await asyncio.sleep(2 * (attempt + 1))


async def job(context):
    try:
        await send_summary_message()
    except Exception as e:
        print(f"Ошибка при отправке ежедневной сводки: {e}", flush=True)
