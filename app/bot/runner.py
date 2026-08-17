import os
from datetime import time, timezone, timedelta
from dotenv import load_dotenv
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
)

from app.daily_summary import job as daily_summary_job
from app.bot.handlers.report import report_company_callback, report_command
from app.metrics import start_metrics
from app.settings import BOT_TOKEN
from app.bot.callbacks import handle_rating_callback

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

    job_queue = app.job_queue

    app.add_handler(
        CallbackQueryHandler(
            handle_rating_callback,
            pattern=r"^(rate|edit_rate|niche|intent|rate_back):",
        )
    )
    app.add_handler(
        CommandHandler("report", report_command)
    )
    app.add_handler(
        CallbackQueryHandler(
            report_company_callback,
            pattern=r"^report_company:\d+$",
        )
    )

    print("🤖 Бот запущен", flush=True)

    if job_queue is None:
        raise RuntimeError("JobQueue недоступен")

    try:
        # Moscow time = UTC+3
        msk_tz = timezone(timedelta(hours=3))
        job_queue.run_daily(
            daily_summary_job,
            time=time(hour=0, minute=0, tzinfo=msk_tz)
        )
    except Exception as e:
        print(f"Не удалось зарегистрировать ежедневную сводку: {e}", flush=True)


    app.run_polling()


if __name__ == "__main__":
    run_bot()
