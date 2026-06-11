from telegram import (
    Bot,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update
)

from telegram.ext import (
    Application,
    CallbackQueryHandler
)

import uuid
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import os


load_dotenv()


BOT_TOKEN = os.getenv("BOT_TOKEN")
LEADS_CHAT_ID = int(os.getenv("LEADS_CHAT_ID"))

BASE_DIR = Path(__file__).parent


bot = Bot(BOT_TOKEN)


# -----------------------
# временное хранилище лидов
# -----------------------

def save_pending_lead(lead_id, data):

    path = BASE_DIR / "config" / "pending_leads.json"

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



def load_pending_lead(lead_id):

    path = BASE_DIR / "config" / "pending_leads.json"

    try:
        storage = json.loads(
            path.read_text(encoding="utf-8")
        )
    except:
        return None

    return storage.get(lead_id)



# -----------------------
# отправка лида
# -----------------------

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
        ]
    ]


    message = f"""
🔥 НОВЫЙ ЛИД

📊 Score: {result['score']}
📂 Category: {result['category']}

💬 Сообщение:
{result['text']}
"""


    await bot.send_message(
        chat_id=LEADS_CHAT_ID,
        text=message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )



# -----------------------
# обработчик кнопок
# -----------------------

async def button_handler(update: Update, context):

    query = update.callback_query

    await query.answer()


    action, lead_id = query.data.split(":")


    lead = load_pending_lead(lead_id)


    if not lead:
        await query.answer(
            "❌ Лид не найден",
            show_alert=True
        )
        return



    if action == "good":

        rating = "good"
        mark = "👍 Оценка: хороший лид"


    else:

        rating = "bad"
        mark = "👎 Оценка: плохой лид"



    save_feedback(
        lead,
        rating
    )

    # обновляем текст (без трогания логики)
    old_text = query.message.text

    new_text = old_text + f"\n\n{mark}"

    # 1. сначала обновляем текст
    await query.message.edit_text(new_text)

    # 2. отдельно убираем кнопки (ВАЖНО)
    await query.message.edit_reply_markup(reply_markup=None)



# -----------------------
# обучение
# -----------------------

def save_feedback(lead, rating):

    path = BASE_DIR / "config" / "memory.json"


    try:
        memory = json.loads(
            path.read_text(encoding="utf-8")
        )

    except:
        memory = []


    memory.append(
        {
            "text": lead["text"],
            "score": lead["score"],
            "category": lead["category"],
            "rating": rating,
            "time": str(datetime.now())
        }
    )


    path.write_text(
        json.dumps(
            memory,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )



# -----------------------
# запуск бота
# -----------------------

def run_bot():

    app = Application.builder()\
        .token(BOT_TOKEN)\
        .build()


    app.add_handler(
        CallbackQueryHandler(button_handler)
    )


    app.run_polling()


if __name__ == "__main__":
    run_bot()