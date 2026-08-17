from telegram import InlineKeyboardButton

from app.types import LeadResultId


def build_niche_question_keyboard(lead_result_id: LeadResultId):
    """Первый шаг оценки: совпала ли тема ниши."""

    return [
        [
            InlineKeyboardButton(
                "✅ Да",
                callback_data=f"niche:{lead_result_id}:da",
            ),
            InlineKeyboardButton(
                "❌ Нет",
                callback_data=f"niche:{lead_result_id}:net",
            ),
        ],
        [
            InlineKeyboardButton(
                "🚫 Спам",
                callback_data=f"rate:{lead_result_id}:spam",
            ),
            InlineKeyboardButton(
                "⏭️ Пропустить",
                callback_data=f"rate:{lead_result_id}:skip",
            ),
        ],
    ]


def build_intent_question_keyboard(lead_result_id: LeadResultId):
    """
    Второй шаг оценки: нужна ли CURRENT_USER помощь.
    Показывается только после подтверждения совпадения темы.
    """

    return [
        [
            InlineKeyboardButton(
                "✅ Да",
                callback_data=f"intent:{lead_result_id}:da",
            ),
            InlineKeyboardButton(
                "❌ Нет",
                callback_data=f"intent:{lead_result_id}:net",
            ),
        ],
        [
            InlineKeyboardButton(
                "⬅️ Назад",
                callback_data=f"rate_back:{lead_result_id}",
            ),
        ],
    ]


def build_edit_rating_keyboard(lead_result_id: LeadResultId):
    return [
        [
            InlineKeyboardButton(
                "✏️ Изменить",
                callback_data=f"edit_rate:{lead_result_id}",
            )
        ]
    ]