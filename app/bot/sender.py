import uuid
import asyncio
from telegram import (
    Bot,
    InlineKeyboardMarkup,
)
from telegram.request import HTTPXRequest

from app.settings import CHAT_ID, BOT_TOKEN, LEADS_TOPIC_ID
from telegram.error import TimedOut, NetworkError, RetryAfter

from .keyboards import build_rating_keyboard
from .messages import build_lead_message
from .storage import save_pending_lead

request = HTTPXRequest(
    connect_timeout=30,
    read_timeout=30,
    write_timeout=30,
    pool_timeout=30,
)

bot = Bot(
    BOT_TOKEN,
    request=request
)


async def send_to_leads(result):
    lead_id = str(uuid.uuid4())[:8]

    save_pending_lead(
        lead_id,
        result
    )

    for attempt in range(3):
        try:
            await bot.send_message(
                chat_id=CHAT_ID,
                text=build_lead_message(result),
                message_thread_id=LEADS_TOPIC_ID,
                reply_markup=InlineKeyboardMarkup(
                    build_rating_keyboard(lead_id)
                ),
                parse_mode="HTML"
            )
            return True

        except RetryAfter as e:
            wait_seconds = int(getattr(e, "retry_after", 10))

            print(
                f"⏳ Telegram ограничил отправку. Ждём {wait_seconds} сек.",
                flush=True
            )

            await asyncio.sleep(wait_seconds)

        except (TimedOut, NetworkError) as e:
            wait_seconds = 5 * (attempt + 1)

            print(
                f"⚠️ Ошибка сети при отправке лида. "
                f"Попытка {attempt + 1}/3. Ждём {wait_seconds} сек. Ошибка: {e}",
                flush=True
            )

            await asyncio.sleep(wait_seconds)

        except Exception as e:
            print(
                f"❌ Неожиданная ошибка при отправке лида: {e}",
                flush=True
            )
            return False

    print(
        "❌ Не удалось отправить лид после 3 попыток",
        flush=True
    )

    return False
