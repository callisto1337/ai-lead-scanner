from telegram import InlineKeyboardButton


def build_rating_keyboard(lead_result_id: int):
    return [
        [
            InlineKeyboardButton(
                "👍 Хороший",
                callback_data=f"rate:{lead_result_id}:good",
            ),
            InlineKeyboardButton(
                "👎 Плохой",
                callback_data=f"rate:{lead_result_id}:bad",
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


def build_edit_rating_keyboard(lead_result_id: int):
    return [
        [
            InlineKeyboardButton(
                "✏️ Изменить",
                callback_data=f"edit_rate:{lead_result_id}",
            )
        ]
    ]