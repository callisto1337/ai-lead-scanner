import asyncio

from telegram import Bot, InlineKeyboardMarkup
from telegram.error import TimedOut, NetworkError, RetryAfter
from telegram.request import HTTPXRequest

from app.settings import BOT_TOKEN
from app.bot.keyboards import build_rating_keyboard
from app.bot.messages import build_lead_message
from app.metrics import telegram_send_errors


request = HTTPXRequest(
    connect_timeout=60,
    read_timeout=60,
    write_timeout=60,
    pool_timeout=60,
)

bot = Bot(
    BOT_TOKEN,
    request=request,
)


async def send_to_leads(
    lead_result_id: int,
    result: dict,
    telegram_config: dict,
) -> bool:
    leads_topic_id = telegram_config.get("leads_topic_id")

    text = build_lead_message(
        result=result
    )

    max_len = 3900

    if len(text) > max_len:
        text = text[:max_len] + "\n\n…сообщение обрезано"

    kwargs = {
        "chat_id": telegram_config["chat_id"],
        "text": text,
        "reply_markup": InlineKeyboardMarkup(
            build_rating_keyboard(lead_result_id)
        ),
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    if leads_topic_id:
        kwargs["message_thread_id"] = leads_topic_id

    for attempt in range(1, 4):
        try:
            message = await bot.send_message(**kwargs)

            print(
                f"✅ Лид отправлен lead_result_id={lead_result_id}, "
                f"telegram_message_id={message.message_id}",
                flush=True,
            )

            return True

        except RetryAfter as e:
            wait_seconds = int(e.retry_after) + 1

            print(
                f"⏳ Telegram RetryAfter {wait_seconds}s "
                f"lead_result_id={lead_result_id}",
                flush=True,
            )

            await asyncio.sleep(wait_seconds)

        except (TimedOut, NetworkError) as e:
            telegram_send_errors.inc()

            print(
                f"⚠️ Telegram timeout/network error "
                f"attempt={attempt}/3 "
                f"lead_result_id={lead_result_id}: "
                f"{type(e).__name__}: {e}",
                flush=True,
            )

            if attempt == 3:
                return False

            await asyncio.sleep(2 * attempt)

        except Exception as e:
            telegram_send_errors.inc()

            print(
                f"❌ Telegram send failed "
                f"lead_result_id={lead_result_id}: "
                f"{type(e).__name__}: {e}",
                flush=True,
            )

            return False

    return False