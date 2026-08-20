from html import escape

from telegram import Update, InlineKeyboardMarkup, User, Message, CallbackQuery
from telegram.ext import ContextTypes

from app.bot.keyboards import (
    build_niche_question_keyboard,
    build_intent_question_keyboard,
    build_edit_rating_keyboard,
)
from app.bot.messages import NICHE_QUESTION_TEXT, INTENT_QUESTION_TEXT
from app.db.feedback import update_lead_feedback
from app.db.leads import get_user_id_by_lead_result_id
from app.db.blacklist_users import add_blacklisted_user
from app.metrics import feedback_total
from app.types import LeadResultId, RatingData, TgUserId

FEEDBACK_MARKER = "\n\n<b>Оценка оператора</b>"
QUESTION_TEXTS = (NICHE_QUESTION_TEXT, INTENT_QUESTION_TEXT)


def get_rating_data(rating: str) -> RatingData | None:
    """Оценки, не связанные с осями ниша/намерение: спам и пропуск."""

    if rating == "spam":
        return RatingData(
            feedback="spam",
            human_lead=None,
            niche_match=None,
            intent_match=None,
            label="🚫 спам",
            text="🚫 Оценка: спам",
        )

    if rating == "skip":
        return RatingData(
            feedback="skip",
            human_lead=None,
            niche_match=None,
            intent_match=None,
            label="⏭️ пропущено",
            text="⏭️ Оценка: пропущено",
        )

    return None


def get_axis_rating_data(
    niche_match: str,
    intent_match: str | None,
) -> RatingData:
    """
    Собирает итоговую оценку из ответов на два вопроса оператора.
    Если тема не совпала — намерение не спрашивается,
    итог сразу отрицательный.
    """

    if niche_match == "нет":
        return RatingData(
            feedback="bad",
            human_lead=False,
            niche_match="нет",
            intent_match=None,
            label="❌ тема не совпала",
            text="❌ Оценка: тема не совпала",
        )

    if intent_match == "да":
        return RatingData(
            feedback="good",
            human_lead=True,
            niche_match="да",
            intent_match="да",
            label="✅ тема совпала, нужна помощь",
            text="✅ Оценка: тема совпала, нужна помощь",
        )

    return RatingData(
        feedback="bad",
        human_lead=False,
        niche_match="да",
        intent_match="нет",
        label="✅ тема, ❌ помощь не нужна",
        text="❌ Оценка: тема совпала, помощь не нужна",
    )


def get_rater_text(user: User) -> str:
    if user.username:
        return f"@{user.username}"

    if user.full_name:
        return f"{user.full_name} (ID: {user.id})"

    return f"ID: {user.id}"


def strip_feedback_block(text: str) -> str:
    if FEEDBACK_MARKER in text:
        return text.split(FEEDBACK_MARKER)[0].rstrip()

    return text.rstrip()


def strip_question_line(text: str) -> str:
    stripped = text.rstrip()

    for question in QUESTION_TEXTS:
        suffix = f"\n\n{question}"

        if stripped.endswith(suffix):
            return stripped[: -len(suffix)].rstrip()

    return stripped


def clean_message_text(text: str) -> str:
    return strip_question_line(strip_feedback_block(text))


def build_message_with_feedback(
    original_html: str,
    rating_text: str,
    rater_text: str,
) -> str:
    clean_html = clean_message_text(original_html)

    return f"""{clean_html}{FEEDBACK_MARKER}
{escape(rating_text)}
👨🏻‍💼 Оценил: {escape(rater_text)}"""


async def finalize_rating(
    query: CallbackQuery,
    message: Message,
    lead_result_id: LeadResultId,
    rating_data: RatingData,
) -> None:
    user = query.from_user
    rater_text = get_rater_text(user)

    ok = update_lead_feedback(
        lead_result_id=lead_result_id,
        feedback=rating_data["feedback"],
        human_lead=rating_data["human_lead"],
        niche_match=rating_data["niche_match"],
        intent_match=rating_data["intent_match"],
        rated_by={
            "id": user.id,
            "username": user.username,
            "name": user.full_name,
        },
    )

    if not ok:
        await query.answer(
            "Лид не найден",
            show_alert=True,
        )
        return

    feedback_total.labels(
        feedback=rating_data["feedback"]
    ).inc()

    if rating_data["feedback"] == "spam":
        spam_user_id = get_user_id_by_lead_result_id(
            lead_result_id
        )

        if spam_user_id:
            add_blacklisted_user(
                user_id=spam_user_id,
                reason=(
                    "spam_feedback: "
                    f"lead_result_id={lead_result_id}"
                ),
                created_by=TgUserId(user.id),
            )

            print(
                (
                    "🚫 Пользователь добавлен в blacklist: "
                    f"user_id={spam_user_id}, "
                    f"lead_result_id={lead_result_id}"
                ),
                flush=True,
            )
        else:
            print(
                (
                    "⚠️ Не удалось найти user_id для spam "
                    f"lead_result_id={lead_result_id}"
                ),
                flush=True,
            )

    original_html = message.text_html or message.text or ""

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

    await query.answer(
        f"Оценка сохранена: {rating_data['label']}"
    )


def parse_lead_result_id(raw: str) -> LeadResultId | None:
    try:
        return LeadResultId(int(raw))
    except ValueError:
        return None


async def handle_rating_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    query = update.callback_query

    if query is None:
        return

    data = query.data or ""
    print("🔘 CALLBACK:", data, flush=True)

    await query.answer()

    message = query.message

    if not isinstance(message, Message):
        await query.answer(
            "Исходное сообщение недоступно",
            show_alert=True,
        )
        return

    if data.startswith("edit_rate:"):
        _, lead_result_id_raw = data.split(":")
        lead_result_id = parse_lead_result_id(lead_result_id_raw)

        if lead_result_id is None:
            await query.answer(
                "Некорректные данные",
                show_alert=True,
            )
            return

        original_html = message.text_html or message.text or ""
        clean_html = clean_message_text(original_html)
        new_text = f"{clean_html}\n\n{NICHE_QUESTION_TEXT}"

        await query.edit_message_text(
            text=new_text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                build_niche_question_keyboard(lead_result_id)
            ),
            disable_web_page_preview=True,
        )

        return

    if data.startswith("rate_back:"):
        _, lead_result_id_raw = data.split(":")
        lead_result_id = parse_lead_result_id(lead_result_id_raw)

        if lead_result_id is None:
            await query.answer(
                "Некорректные данные",
                show_alert=True,
            )
            return

        original_html = message.text_html or message.text or ""
        clean_html = clean_message_text(original_html)
        new_text = f"{clean_html}\n\n{NICHE_QUESTION_TEXT}"

        await query.edit_message_text(
            text=new_text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                build_niche_question_keyboard(lead_result_id)
            ),
            disable_web_page_preview=True,
        )

        return

    if data.startswith("niche:"):
        try:
            _, lead_result_id_raw, answer = data.split(":")
        except ValueError:
            await query.answer(
                "Некорректные данные",
                show_alert=True,
            )
            return

        lead_result_id = parse_lead_result_id(lead_result_id_raw)

        if lead_result_id is None:
            await query.answer(
                "Некорректный ID лида",
                show_alert=True,
            )
            return

        if answer == "net":
            rating_data = get_axis_rating_data(
                niche_match="нет",
                intent_match=None,
            )
            await finalize_rating(
                query, message, lead_result_id, rating_data
            )
            return

        if answer == "da":
            original_html = message.text_html or message.text or ""
            clean_html = clean_message_text(original_html)
            new_text = f"{clean_html}\n\n{INTENT_QUESTION_TEXT}"

            await query.edit_message_text(
                text=new_text,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(
                    build_intent_question_keyboard(lead_result_id)
                ),
                disable_web_page_preview=True,
            )
            return

        await query.answer(
            "Некорректный ответ",
            show_alert=True,
        )
        return

    if data.startswith("intent:"):
        try:
            _, lead_result_id_raw, answer = data.split(":")
        except ValueError:
            await query.answer(
                "Некорректные данные",
                show_alert=True,
            )
            return

        lead_result_id = parse_lead_result_id(lead_result_id_raw)

        if lead_result_id is None:
            await query.answer(
                "Некорректный ID лида",
                show_alert=True,
            )
            return

        if answer not in ("da", "net"):
            await query.answer(
                "Некорректный ответ",
                show_alert=True,
            )
            return

        rating_data = get_axis_rating_data(
            niche_match="да",
            intent_match="да" if answer == "da" else "нет",
        )
        await finalize_rating(
            query, message, lead_result_id, rating_data
        )
        return

    try:
        action, lead_result_id_raw, rating = data.split(":")
    except ValueError:
        await query.answer(
            "Некорректные данные",
            show_alert=True,
        )
        return

    if action != "rate":
        return

    lead_result_id = parse_lead_result_id(lead_result_id_raw)

    if lead_result_id is None:
        await query.answer(
            "Некорректный ID лида",
            show_alert=True,
        )
        return

    rating_data = get_rating_data(rating)

    if not rating_data:
        await query.answer(
            "Неизвестная оценка",
            show_alert=True,
        )
        return

    await finalize_rating(query, message, lead_result_id, rating_data)
