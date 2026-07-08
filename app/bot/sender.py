from telegram import Bot, InlineKeyboardMarkup
from telegram.request import HTTPXRequest

from app.settings import BOT_TOKEN
from app.bot.keyboards import build_rating_keyboard
from app.bot.messages import build_lead_message


request = HTTPXRequest(
    connect_timeout=30,
    read_timeout=30,
    write_timeout=30,
    pool_timeout=30,
)

bot = Bot(
    BOT_TOKEN,
    request=request,
)


async def send_to_leads(
    lead_result_id: int,
    result: dict,
    context: list[str],
    telegram_config: dict,
) -> bool:
    leads_topic_id = telegram_config.get("leads_topic_id")

    kwargs = {
        "chat_id": telegram_config["chat_id"],
        "text": build_lead_message(
            lead=result,
            history=context,
        ),
        "reply_markup": InlineKeyboardMarkup(
            build_rating_keyboard(lead_result_id)
        ),
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    if leads_topic_id:
        kwargs["message_thread_id"] = leads_topic_id

    print(
        f"📨 bot.send_message kwargs: "
        f"chat_id={kwargs.get('chat_id')}, "
        f"message_thread_id={kwargs.get('message_thread_id')}",
        flush=True,
    )

    message = await bot.send_message(**kwargs)

    print(
        f"✅ Лид отправлен: telegram_message_id={message.message_id}",
        flush=True,
    )

    return True
