import asyncio
from datetime import datetime
from telegram import Bot

from app.db.connection import get_connection
from app.db.daily_summary import format_period, get_last_24_hours_period, get_active_summary_targets, \
    get_daily_summary_stats
from app.settings import BOT_TOKEN


async def send_company_summary(company_id: int) -> None:
    started_at, ended_at = get_last_24_hours_period()

    with get_connection() as conn:
        target = conn.execute(
            """
            SELECT
                tc.company_id,
                tc.chat_id,
                tc.metrics_topic_id,
                c.name AS company_name
            FROM telegram_configs tc

            JOIN companies c
                ON c.id = tc.company_id

            WHERE tc.company_id = %s
              AND tc.is_active = TRUE
              AND c.is_active = TRUE
              AND tc.chat_id IS NOT NULL

            LIMIT 1
            """,
            (company_id,),
        ).fetchone()

    if target is None:
        raise ValueError(
            f"Не найдена активная Telegram-конфигурация company_id={company_id}"
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

    bot = Bot(BOT_TOKEN)

    await send_message_with_retry(
        bot=bot,
        chat_id=target["chat_id"],
        text=text,
        metrics_topic_id=target["metrics_topic_id"],
    )

    print(
        (
            "✅ Ежедневная сводка отправлена вручную: "
            f"company_id={company_id}, "
            f"company={target['company_name']}"
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
    metrics_topic_id: int | None,
) -> None:
    send_kwargs = {
        "chat_id": chat_id,
        "text": text,
    }

    # Значение 0 означает общий раздел группы.
    # В таком случае message_thread_id передавать не нужно.
    if metrics_topic_id:
        send_kwargs["message_thread_id"] = metrics_topic_id

    for attempt in range(3):
        try:
            await bot.send_message(**send_kwargs)
            return
        except Exception as error:
            print(
                (
                    "⚠️ Ошибка отправки ежедневной сводки. "
                    f"Попытка {attempt + 1}/3: {error}"
                ),
                flush=True,
            )

            if attempt < 2:
                await asyncio.sleep(2 * (attempt + 1))

    raise RuntimeError(
        f"Не удалось отправить сводку в chat_id={chat_id}"
    )


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
                metrics_topic_id=target["metrics_topic_id"],
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