from telegram import (
    Bot,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    ContextTypes
)

from dotenv import load_dotenv

from pathlib import Path
import os
import json
import uuid
import html
from datetime import datetime


load_dotenv()


BOT_TOKEN = os.getenv("BOT_TOKEN")
LEADS_CHAT_ID = int(os.getenv("LEADS_CHAT_ID"))
BASE_DIR = Path(__file__).parent

bot = Bot(BOT_TOKEN)


# ---------------- STORAGE ----------------


def pending_path():
    return BASE_DIR / "config" / "pending_leads.json"



def memory_path():
    return BASE_DIR / "config" / "memory.json"



def blacklist_path():
    return BASE_DIR / "config" / "blacklist.txt"



def add_to_blacklist(value):

    if not value:
        return

    value = str(value).strip()

    if not value:
        return

    path = blacklist_path()

    try:
        existing = {
            line.strip()
            for line in path.read_text(
                encoding="utf-8"
            ).splitlines()
            if line.strip()
        }

    except:
        existing = set()


    if value in existing:
        return


    existing.add(value)


    path.write_text(
        "\n".join(sorted(existing)) + "\n",
        encoding="utf-8"
    )


def save_pending_lead(lead_id, data):

    path = pending_path()

    try:
        storage = json.loads(
            path.read_text(encoding="utf-8")
        )
    except:
        storage = {}


    storage[lead_id] = data


    path.write_text(
        json.dumps(
            storage,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )



def load_pending_leads():

    try:
        return json.loads(
            pending_path().read_text(
                encoding="utf-8"
            )
        )

    except:
        return {}



def save_memory(item):

    path = memory_path()

    try:
        memory = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    except:
        memory = []


    memory.append(item)


    memory = memory[-200:]


    path.write_text(
        json.dumps(
            memory,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )



# ---------------- SEND ----------------


async def send_to_leads(result):

    lead_id = str(uuid.uuid4())[:8]


    save_pending_lead(
        lead_id,
        result
    )


    keyboard = [
        [
            InlineKeyboardButton(
                "👍 Хороший",
                callback_data=f"good:{lead_id}"
            ),

            InlineKeyboardButton(
                "👎 Плохой",
                callback_data=f"bad:{lead_id}"
            )
        ],
        [
            InlineKeyboardButton(
                "🚫 Спам / Игнор",
                callback_data=f"spam:{lead_id}"
            )
        ]
    ]


    message = f"""
    🔥 НОВЫЙ ЛИД
    
    💬 Сообщение:
    {html.escape(result["text"])}
    
    👤 Пользователь:
    {result.get("user_link", "нет ссылки")}
    
    🔗 Источник:
    {html.escape(result.get("link", "нет ссылки"))}
    """


    await bot.send_message(
        chat_id=LEADS_CHAT_ID,
        text=message,
        reply_markup=InlineKeyboardMarkup(
            keyboard
        ),
        parse_mode="HTML"
    )


# ---------------- BUTTONS ----------------


async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    if not query or not query.data:
        return

    await query.answer()

    try:
        action, lead_id = query.data.split(":", 1)
    except ValueError:
        await query.answer(
            "Некорректные данные кнопки",
            show_alert=True
        )
        return

    pending = load_pending_leads()

    lead = pending.get(lead_id)

    if not lead:

        await query.answer(
            "Лид не найден",
            show_alert=True
        )

        return

    if action == "good":

        rating_text = "👍 Оценка: хороший лид"
        feedback = "good"
        is_lead = True

    elif action == "bad":

        rating_text = "👎 Оценка: плохой лид"
        feedback = "bad"
        is_lead = False

    elif action == "spam":

        rating_text = "🚫 Оценка: спам / игнор"
        feedback = "spam"
        is_lead = False

        add_to_blacklist(
            lead.get("user_id")
        )

    else:

        await query.answer(
            "Неизвестное действие",
            show_alert=True
        )

        return

    if feedback != "spam":

        save_memory({
            "text": lead["text"],
            "lead": is_lead,
            "feedback": feedback,
            "time": str(datetime.now())
        })

    old_text = query.message.text

    await query.edit_message_text(
        text=old_text + "\n\n" + rating_text,
        reply_markup=None
    )



# ---------------- RUN ----------------


def run_bot():

    app = Application.builder()\
        .token(BOT_TOKEN)\
        .build()


    app.add_handler(
        CallbackQueryHandler(
            button_handler
        )
    )


    app.run_polling()



if __name__ == "__main__":

    run_bot()