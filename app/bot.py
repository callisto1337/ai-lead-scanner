from telegram import (
    Bot,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update
)
from telegram.error import TimedOut, NetworkError, RetryAfter
from telegram.request import HTTPXRequest
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    ContextTypes,
    CommandHandler,
)
from daily_summary import send_summary_message
from dotenv import load_dotenv

from metrics import lead_approved, lead_rejected, lead_skipped, lead_blocked
from settings import BOT_TOKEN, BASE_DIR, CHAT_ID, LEADS_TOPIC_ID

import json
import uuid
import html
import asyncio
from datetime import datetime
from memory import save_memory


load_dotenv()
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


# ---------------- STORAGE ----------------


def pending_path():
    return BASE_DIR / "config" / "pending_leads.json"


def ensure_pending_storage():
    path = pending_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    if not path.exists():
        path.write_text(
            "{}",
            encoding="utf-8"
        )



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

    ensure_pending_storage()

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

    ensure_pending_storage()

    try:
        return json.loads(
            pending_path().read_text(
                encoding="utf-8"
            )
        )

    except:
        return {}


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
        ],
        [
            InlineKeyboardButton(
                "⏭️ Пропустить",
                callback_data=f"skip:{lead_id}"
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


    for attempt in range(3):
        try:
            await bot.send_message(
                chat_id=CHAT_ID,
                text=message,
                message_thread_id=LEADS_TOPIC_ID,
                reply_markup=InlineKeyboardMarkup(
                    keyboard
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


# ---------------- COMMANDS ----------------


async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text("📋 Отправляю отчет...")
        print("🔍 Начинаю отправку отчета...", flush=True)
        await send_summary_message()
        print("✅ Отчет успешно отправлен", flush=True)
    except Exception as e:
        print(f"❌ Ошибка при отправке отчета: {e}", flush=True)
        await update.message.reply_text(f"❌ Ошибка: {e}")


# ---------------- BUTTONS ----------------


async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE, # не удалять!!
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

        lead_approved()

    elif action == "bad":

        rating_text = "👎 Оценка: плохой лид"
        feedback = "bad"
        is_lead = False

        lead_rejected()

    elif action == "spam":

        rating_text = "🚫 Оценка: спам / игнор"
        feedback = "spam"
        is_lead = False

        lead_blocked(
            lead.get("user_id")
        )
        add_to_blacklist(
            lead.get("user_id")
        )

    elif action == "skip":

        rating_text = "⏭️ Оценка: пропущено"
        feedback = "skip"
        is_lead = None

        lead_skipped()

    else:

        await query.answer(
            "Неизвестное действие",
            show_alert=True
        )

        return

    if feedback not in ("spam", "skip"):

        save_memory({
            "text": lead["text"],
            "lead": is_lead,
            "feedback": feedback,
            "time": str(datetime.now()),
            "description": lead["description"],
        })

    old_text = query.message.text

    await query.edit_message_text(
        text=old_text + "\n\n" + rating_text,
        reply_markup=None
    )



# ---------------- RUN ----------------


def run_bot():

    print("🚀 Запуск бота...")

    app = Application.builder()\
        .token(BOT_TOKEN)\
        .build()


    app.add_handler(
        CallbackQueryHandler(
            button_handler
        )
    )
    app.add_handler(
        CommandHandler("report", report_command)
    )

    print("🤖 Бот запущен", flush=True)

    try:
        from daily_summary import job as daily_summary_job
        from datetime import time, timezone, timedelta

        # Moscow time = UTC+3
        msk_tz = timezone(timedelta(hours=3))
        app.job_queue.run_daily(daily_summary_job, time=time(hour=0, minute=0, tzinfo=msk_tz))
    except Exception as e:
        print(f"Не удалось зарегистрировать ежедневную сводку: {e}", flush=True)


    app.run_polling()




if __name__ == "__main__":

    run_bot()