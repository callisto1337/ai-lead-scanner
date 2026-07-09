import os
from prometheus_client import start_http_server
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
    METRICS_PORT = int(os.getenv("BOT_METRICS_PORT", "8003"))
    start_metrics(METRICS_PORT, "Bot")

    print(
        f"📊 Метрики бота запущены на: {METRICS_PORT}/metrics",
        flush=True,
    )

    print("🚀 Запуск бота...")

    load_dotenv()

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
