import asyncio
from datetime import datetime
from telegram import Bot

from app.db.companies import get_company_by_id
from app.db.daily_summary import format_period, get_last_24_hours_period, get_active_summary_targets, \
    get_daily_summary_stats
from app.db.telegram_configs import get_telegram_config_by_company
from app.settings import BOT_TOKEN


async def send_company_summary(
    company_id: int,
    chat_id: int | None = None,
) -> None:
    started_at, ended_at = get_last_24_hours_period()

    company = get_company_by_id(company_id)
    config = get_telegram_config_by_company(company_id)

    if company is None:
        raise ValueError(f"Компания company_id={company_id} не найдена")

    if config is None:
        raise ValueError(
            f"Telegram-конфигурация company_id={company_id} не найдена"
        )

    stats = get_daily_summary_stats(
        company_id=company_id,
        started_at=started_at,
        ended_at=ended_at,
    )

    text = build_daily_summary_message(
        stats=stats,
        started_at=started_at,
        ended_at=ended_at,
    )

    target_chat_id = (
        chat_id
        if chat_id is not None
        else config.get("chat_id")
    )

    if not target_chat_id:
        raise ValueError(
            f"Не указан chat_id для company_id={company_id}"
        )

    target_thread_id = (
        None
        if chat_id is not None
        else config.get("metrics_topic_id")
    )

    bot = Bot(BOT_TOKEN)

    await send_message_with_retry(
        bot=bot,
        chat_id=target_chat_id,
        text=text,
        message_thread_id=target_thread_id,
    )

    print(
        (
            "✅ Сводка отправлена: "
            f"company_id={company_id}, "
            f"company={company['company_name']}, "
            f"chat_id={target_chat_id}, "
            f"thread_id={target_thread_id}"
        ),
        flush=True,
    )


def build_daily_summary_message(
    stats: list[dict],
    started_at: datetime,
    ended_at: datetime,
) -> str:
    blocks = [
        "📊 Сводка за последние 24 часа",
        f"🕒 {format_period(started_at, ended_at)}",
    ]

    if not stats:
        blocks.append("\nНет активных ниш.")
        return "\n".join(blocks)

    for item in stats:
        blocks.append(
            "\n".join(
                [
                    "",
                    f"Найдено лидов: {item['leads_found']}",
                    "",
                    f"Оценено оператором: {item['rated']}",
                    f"👍 Хороших: {item['good']}",
                    f"👎 Плохих: {item['bad']}",
                    f"⏭️ Skip: {item['skipped']}",
                    f"🚫 Spam: {item['spam']}",
                    "",
                ]
            )
        )

    return "\n".join(blocks)


async def send_message_with_retry(
    bot: Bot,
    chat_id: int,
    text: str,
    message_thread_id: int | None = None,
) -> None:
    send_kwargs = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }
    attempts = 0

    if message_thread_id:
        send_kwargs["message_thread_id"] = message_thread_id

    for attempt in range(1, attempts + 1):
        try:
            await bot.send_message(**send_kwargs)
            return

        except Exception as exc:
            print(
                (
                    "⚠️ Ошибка отправки ежедневной сводки. "
                    f"Попытка {attempt}/{attempts}: {exc}"
                ),
                flush=True,
            )

            if attempt == attempts:
                raise RuntimeError(
                    f"Не удалось отправить сводку в chat_id={chat_id}"
                ) from exc


async def send_summary_messages() -> None:
    started_at, ended_at = get_last_24_hours_period()
    targets = get_active_summary_targets()

    bot = Bot(BOT_TOKEN)

    for target in targets:
        try:
            stats = get_daily_summary_stats(
                company_id=target["company_id"],
                started_at=started_at,
                ended_at=ended_at,
            )

            text = build_daily_summary_message(
                stats=stats,
                started_at=started_at,
                ended_at=ended_at,
            )

            await send_message_with_retry(
                bot=bot,
                chat_id=target["chat_id"],
                text=text,
            )

            print(
                (
                    "✅ Ежедневная сводка отправлена: "
                    f"company_id={target['company_id']}, "
                    f"company={target['company_name']}"
                ),
                flush=True,
            )

        except Exception as error:
            print(
                (
                    "❌ Ошибка отправки сводки: "
                    f"company_id={target['company_id']}, "
                    f"company={target['company_name']}, "
                    f"chat_id={target['chat_id']}, "
                    f"metrics_topic_id={target['metrics_topic_id']}, "
                    f"error={error}"
                ),
                flush=True,
            )


async def job(context=None) -> None:
    try:
        await send_summary_messages()
    except Exception as error:
        print(
            f"❌ Ошибка при отправке ежедневной сводки: {error}",
            flush=True,
        )


if __name__ == "__main__":
    asyncio.run(send_summary_messages())