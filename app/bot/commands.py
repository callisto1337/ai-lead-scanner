from telegram import Update
from telegram.ext import ContextTypes

from .daily_summary import send_summary_message


async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text("📋 Отправляю отчет...")
        print("🔍 Начинаю отправку отчета...", flush=True)
        await send_summary_message()
        print("✅ Отчет успешно отправлен", flush=True)
    except Exception as e:
        print(f"❌ Ошибка при отправке отчета: {e}", flush=True)
        await update.message.reply_text(f"❌ Ошибка: {e}")
