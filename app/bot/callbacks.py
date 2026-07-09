from html import escape

from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from app.bot.keyboards import (
    build_rating_keyboard,
    build_edit_rating_keyboard,
)
from app.db.feedback import update_lead_feedback
from app.db.leads import get_user_id_by_lead_result_id
from app.db.blacklist_users import add_blacklisted_user


FEEDBACK_MARKER = "\n\n<b>Оценка оператора</b>"


def get_rating_data(rating: str):
    if rating == "good":
        return {
            "feedback": "good",
            "human_lead": True,
            "label": "👍 хороший лид",
            "text": "👍 Оценка: хороший лид",
        }

    if rating == "bad":
        return {
            "feedback": "bad",
            "human_lead": False,
            "label": "👎 плохой лид",
            "text": "👎 Оценка: плохой лид",
        }

    if rating == "spam":
        return {
            "feedback": "spam",
            "human_lead": None,
            "label": "🚫 спам",
            "text": "🚫 Оценка: спам",
        }

    if rating == "skip":
        return {
            "feedback": "skip",
            "human_lead": None,
            "label": "⏭️ пропущено",
            "text": "⏭️ Оценка: скип",
        }

    return None


def get_rater_text(user) -> str:
    if user.username:
        return f"@{user.username}"

    if user.full_name:
        return f"{user.full_name} (ID: {user.id})"

    return f"ID: {user.id}"


def strip_feedback_block(text: str) -> str:
    if FEEDBACK_MARKER in text:
        return text.split(FEEDBACK_MARKER)[0].rstrip()

    return text.rstrip()


def build_message_with_feedback(
    original_html: str,
    rating_text: str,
    rater_text: str,
) -> str:
    clean_html = strip_feedback_block(original_html)

    return f"""{clean_html}{FEEDBACK_MARKER}
{escape(rating_text)}
👨🏻‍💼 Оценил: {escape(rater_text)}"""


async def handle_rating_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    if not query:
        return

    data = query.data or ""
    print("🔘 CALLBACK:", data, flush=True)

    await query.answer()

    if data.startswith("edit_rate:"):
        try:
            _, lead_result_id_raw = data.split(":")
            lead_result_id = int(lead_result_id_raw)
        except ValueError:
            await query.answer("Некорректные данные", show_alert=True)
            return

        original_html = query.message.text_html or query.message.text or ""
        clean_html = strip_feedback_block(original_html)

        await query.edit_message_text(
            text=clean_html,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                build_rating_keyboard(lead_result_id)
            ),
            disable_web_page_preview=True,
        )

        return

    try:
        action, lead_result_id_raw, rating = data.split(":")
    except ValueError:
        await query.answer("Некорректные данные", show_alert=True)
        return

    if action != "rate":
        return

    try:
        lead_result_id = int(lead_result_id_raw)
    except ValueError:
        await query.answer("Некорректный ID лида", show_alert=True)
        return

    rating_data = get_rating_data(rating)

    if not rating_data:
        await query.answer("Неизвестная оценка", show_alert=True)
        return

    user = query.from_user
    rater_text = get_rater_text(user)

    ok = update_lead_feedback(
        lead_result_id=lead_result_id,
        feedback=rating_data["feedback"],
        human_lead=rating_data["human_lead"],
        rated_by={
            "id": user.id,
            "username": user.username,
            "name": user.full_name,
        },
    )

    if not ok:
        await query.answer("Лид не найден", show_alert=True)
        return

    if rating_data["feedback"] == "spam":
        spam_user_id = get_user_id_by_lead_result_id(lead_result_id)

        if spam_user_id:
            add_blacklisted_user(
                user_id=spam_user_id,
                reason=f"spam_feedback: lead_result_id={lead_result_id}",
                created_by=user.id,
            )

            print(
                f"🚫 Пользователь добавлен в blacklist: "
                f"user_id={spam_user_id}, lead_result_id={lead_result_id}",
                flush=True,
            )
        else:
            print(
                f"⚠️ Не удалось найти user_id для spam lead_result_id={lead_result_id}",
                flush=True,
            )

    original_html = query.message.text_html or query.message.text or ""

    new_text = build_message_with_feedback(
        original_html=original_html,
        rating_text=rating_data["text"],
        rater_text=rater_text,
    )

    await query.edit_message_text(
        text=new_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            build_edit_rating_keyboard(lead_result_id)
        ),
        disable_web_page_preview=True,
    )

    await query.answer(f"Оценка сохранена: {rating_data['label']}")