import traceback

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from app.settings import BOT_ADMIN_IDS
from app.daily_summary import send_company_summary
from app.db.companies import get_report_companies


def is_admin(user_id: int | None) -> bool:
    return user_id is not None and user_id in BOT_ADMIN_IDS


async def report_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    user = update.effective_user
    chat = update.effective_chat
    message = update.effective_message

    if not user or not message:
        return

    if not is_admin(user.id):
        return

    if not chat or chat.type != "private":
        return

    companies = get_report_companies()

    if not companies:
        await message.reply_text(
            "Нет активных компаний для формирования отчёта."
        )
        return

    keyboard = [
        [
            InlineKeyboardButton(
                text=company["name"],
                callback_data=f"report_company:{company['id']}",
            )
        ]
        for company in companies
    ]

    await message.reply_text(
        "Выберите компанию:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def report_company_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    query = update.callback_query
    user = update.effective_user
    chat = update.effective_chat

    if not query or not user:
        return

    if not is_admin(user.id):
        return

    if not chat or chat.type != "private":
        return

    await query.answer()

    try:
        _, company_id_raw = query.data.split(":", maxsplit=1)
        company_id = int(company_id_raw)
    except (ValueError, AttributeError):
        await query.edit_message_text("Некорректная команда.")
        return

    await query.edit_message_text("Формирую отчёт...")

    try:
        await send_company_summary(
            company_id=company_id,
            chat_id=chat.id,
        )

        await query.edit_message_text(
            "✅ Отчёт отправлен в эту личную переписку."
        )

    except Exception:
        print(
            (
                "❌ Ошибка ручной отправки отчёта: "
                f"company_id={company_id}, "
                f"admin_chat_id={chat.id}"
            ),
            flush=True,
        )
        traceback.print_exc()

        await query.edit_message_text(
            "⚠️ Не удалось сформировать отчёт."
        )