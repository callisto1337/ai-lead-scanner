from telegram import InlineKeyboardButton


def build_rating_keyboard(message_id):
    return [
        [
            InlineKeyboardButton(
                "👍 Хороший",
                callback_data=f"good:{message_id}"
            ),

            InlineKeyboardButton(
                "👎 Плохой",
                callback_data=f"bad:{message_id}"
            )
        ],
        [
            InlineKeyboardButton(
                "🚫 Спам / Игнор",
                callback_data=f"spam:{message_id}"
            )
        ],
        [
            InlineKeyboardButton(
                "⏭️ Пропустить",
                callback_data=f"skip:{message_id}"
            )
        ]
    ]


def build_change_keyboard(message_id):
    return [
        [
            InlineKeyboardButton(
                "✏️ Изменить выбор",
                callback_data=f"change:{message_id}"
            )
        ]
    ]