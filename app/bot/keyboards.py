from telegram import InlineKeyboardButton


def build_rating_keyboard(lead_id):
    return [
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


def build_change_keyboard(lead_id):
    return [
        [
            InlineKeyboardButton(
                "✏️ Изменить выбор",
                callback_data=f"change:{lead_id}"
            )
        ]
    ]