import html
from telegram.ext import ContextTypes
from app.blacklist import add_to_blacklist
from app.db import now_iso, update_message_feedback, get_message, save_message
from app.memory import save_memory, delete_memory
from app.metrics import lead_blocked, lead_approved, lead_rejected, lead_skipped
from telegram import (
    InlineKeyboardMarkup,
    Update
)

from .keyboards import build_rating_keyboard, build_change_keyboard
from .messages import build_lead_message, build_rater_info
from .storage import remove_from_blacklist


async def button_handler(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,  # не удалять!!
):
    query = update.callback_query

    if not query or not query.data:
        return

    await query.answer()

    try:
        action, message_id = query.data.split(":", 1)
    except ValueError:
        await query.answer(
            "Некорректные данные кнопки",
            show_alert=True
        )
        return

    lead = get_message(message_id)

    if not lead:
        await query.answer(
            "Лид не найден",
            show_alert=True
        )

        return

    if action == "change":
        await query.edit_message_text(
            text=build_lead_message(lead),
            reply_markup=InlineKeyboardMarkup(
                build_rating_keyboard(message_id)
            ),
            parse_mode="HTML"
        )

        return

    previous_feedback = lead.get("feedback")

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

        lead_blocked()
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

    if previous_feedback == "spam" and feedback != "spam":
        remove_from_blacklist(
            lead.get("user_id")
        )

    rater = build_rater_info(query.from_user)
    rated_at = now_iso()

    update_message_feedback(
        message_id,
        feedback,
        is_lead,
        rated_at,
        rater
    )

    if feedback not in ("spam", "skip"):
        save_memory({
            "id": message_id,
            "text": lead["text"],
            "lead": is_lead,
            "feedback": feedback,
            "time": rated_at,
            "description": lead["description"],
            "rated_by": rater,
        })
    else:
        delete_memory(message_id)

    rating_block = (
        f"{rating_text}\n"
        f"👨🏻‍💼 Оценил: {html.escape(rater['text'])}"
    )

    await query.edit_message_text(
        text=build_lead_message(
            lead,
            rating_block
        ),
        reply_markup=InlineKeyboardMarkup(
            build_change_keyboard(message_id)
        ),
        parse_mode="HTML"
    )
