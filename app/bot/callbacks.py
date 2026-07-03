import html
from telegram.ext import ContextTypes
from app.db import (
    now_iso,
    update_message_feedback,
    add_to_blacklist,
    remove_from_blacklist,
    get_message_by_id, get_context_chain
)
from app.metrics import lead_blocked, lead_approved, lead_rejected, lead_skipped
from telegram import (
    InlineKeyboardMarkup,
    Update
)

from .keyboards import build_rating_keyboard, build_change_keyboard
from .messages import build_lead_message, build_rater_info


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if not query or not query.data:
        return

    await query.answer()

    try:
        action, message_id = query.data.split(":", 1)
    except ValueError:
        await query.answer("Некорректные данные кнопки", show_alert=True)
        return

    message = get_message_by_id(message_id)

    if not message:
        await query.answer("Сообщение не найдено", show_alert=True)
        return

    context_chain = get_context_chain(
        tg_chat_id=message.get("tg_chat_id"),
        tg_message_id=message.get("tg_message_id"),
        reply_to_tg_message_id=message.get("reply_to_tg_message_id")
    )

    if not message:
        await query.answer(
            "Сообщение не найдено",
            show_alert=True
        )

        return

    if action == "change":
        await query.edit_message_text(
            text=build_lead_message(
                message,
                None,
                context_chain
            ),
            reply_markup=InlineKeyboardMarkup(
                build_rating_keyboard(message_id)
            ),
            parse_mode="HTML"
        )

        remove_from_blacklist(message.get("user_id"))

        return

    previous_feedback = message.get("feedback")

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
            message.get("user_id")
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
            message.get("user_id")
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

    rating_block = (
        f"{rating_text}\n"
        f"👨🏻‍💼 Оценил: {html.escape(rater['text'])}"
    )

    await query.edit_message_text(
        text=build_lead_message(
            message,
            rating_block,
            context_chain
        ),
        reply_markup=InlineKeyboardMarkup(
            build_change_keyboard(message_id)
        ),
        parse_mode="HTML"
    )
