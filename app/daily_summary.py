import asyncio
from datetime import datetime, timezone, timedelta

import httpx
from telegram import Bot

from settings import PROMETHEUS_URL, BOT_TOKEN


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
    except Exception:
        return 0


def query_prometheus(metric_name: str) -> int:
    url = PROMETHEUS_URL.rstrip("/") + "/api/v1/query"
    query = PROM_QUERY_TEMPLATE.format(metric=metric_name)

    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.get(url, params={"query": query})
            r.raise_for_status()
            return _parse_prometheus_increase(r.json())
    except Exception:
        return 0


def build_summary() -> dict:
    """Возвращает статистику за последние 24 часа, беря данные из Prometheus."""
    keys = {
        "messages": "messages_total",
        "spam": "spam_total",
        "leads": "leads_total",
        "ai_requests": "ai_requests_total",
    }

    data = {k: query_prometheus(v) for k, v in keys.items()}
    # Moscow time is UTC+3 (no DST currently) — используем фиксированный оффсет
    data["ts"] = datetime.now(tz=timezone(timedelta(hours=3))).isoformat()
    return data


async def send_summary_message(chat_id: int):
    stats = build_summary()

    text = (
        f"📋 Сводка за последние 24 часа (МСК)\n\n"
        f"Всего сообщений: {stats['messages']}\n"
        f"Спам (фильтрация): {stats['spam']}\n"
        f"Обнаружено лидов: {stats['leads']}\n"
        f"Запросов к AI: {stats['ai_requests']}\n"
        f"\n_Время обновления:_ {stats['ts']}")

    bot = Bot(BOT_TOKEN)

    for attempt in range(3):
        try:
            await bot.send_message(chat_id=chat_id, text=text)
            return
        except Exception:
            await asyncio.sleep(2 * (attempt + 1))


async def job(context):
    """JobQueue wrapper. Отправляем сводку в чат из настроек."""
    from settings import LEADS_CHAT_ID

    try:
        await send_summary_message(LEADS_CHAT_ID)
    except Exception as e:
        print(f"Ошибка при отправке ежедневной сводки: {e}", flush=True)


