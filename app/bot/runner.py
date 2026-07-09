from datetime import time, timezone, timedelta
from dotenv import load_dotenv
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
)

from app.metrics import start_metrics
from app.settings import BOT_TOKEN
from app.bootstrap import bootstrap_app

from .callbacks import handle_rating_callback
from .commands import report_command

bootstrap_app()

def run_bot():
    print("🚀 Запуск бота...")

    load_dotenv()
    start_metrics(8001)

    app = Application.builder() \
        .token(BOT_TOKEN) \
        .build()

    app.add_handler(
        CallbackQueryHandler(handle_rating_callback, pattern=r"^rate:")
    )
    app.add_handler(
        CallbackQueryHandler(
            handle_rating_callback,
            pattern=r"^(rate|edit_rate):",
        )
    )
    app.add_handler(
        CommandHandler("report", report_command)
    )

    print("🤖 Бот запущен", flush=True)

    app.run_polling()


if __name__ == "__main__":
    run_bot()
