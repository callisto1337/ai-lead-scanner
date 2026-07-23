import asyncio
import traceback
from datetime import datetime, timezone

from app.db.lead_results import has_recent_user_lead
from app.metrics import user_lead_cooldown_skipped, message_queue_size, message_processing_delay_seconds
from app.queue import message_queue
from app.db.niches import get_active_niches_with_config
from app.db.telegram_configs import get_telegram_config_by_company
from app.bot.sender import send_to_leads
from app.sender_utils import enrich_sender_info
from app.lead_processor import process_message
from app.settings import USER_LEAD_COOLDOWN_MINUTES
from app.types import MessageQueueItem, ProcessMessageResult, LeadResult


async def process_job(job: MessageQueueItem):
    niches = get_active_niches_with_config()

    if not niches:
        print("⚠️ Нет активных ниш", flush=True)
        print("---------------", flush=True)
        return

    for niche in niches:
        sender_id = job["sender_id"]

        if (
            sender_id is not None
            and has_recent_user_lead(
                user_id=sender_id,
                niche_id=niche["id"],
                message_created_at=job["created_at"],
                cooldown_minutes=USER_LEAD_COOLDOWN_MINUTES,
            )
        ):
            user_lead_cooldown_skipped.labels(
                company_id=str(niche["company_id"]),
                niche_id=str(niche["id"]),
            ).inc()

            print(
                (
                    "⏳ Пропуск сообщения по cooldown: "
                    f"sender_id={sender_id}, "
                    f"company_id={niche['company_id']}, "
                    f"niche_id={niche['id']}, "
                    f"cooldown={USER_LEAD_COOLDOWN_MINUTES}m"
                ),
                flush=True,
            )

            continue

        print(
            (
                f"🔎 Проверка ниши: "
                f"{niche['company_name']} / {niche['name']}"
            ),
            flush=True,
        )

        result: ProcessMessageResult | None = await asyncio.to_thread(
            process_message,
            clean_text=job["clean_text"],
            message_id=job["message_id"],
            niche=niche,
            sender_id=job["sender_id"],
            sender_name=job["sender_name"],
            sender_username=job["sender_username"],
            reply_text=job["reply_text"],
            reply_sender_id=job["reply_sender_id"],
        )

        if not result:
            print("---------------", flush=True)
            continue

        enrich_sender_info(result, job["sender"])

        result["source_link"] = job["source_link"]
        result["source_title"] = job["source_title"]
        result["text"] = job["clean_text"]
        result["reply_text"] = job["reply_text"]

        if result["lead"]:
            print("🔥 Найден лид", flush=True)
        else:
            print("❌ Нерелевантное сообщение", flush=True)

        print(
            f"🤖 Объяснение: {result.get('description', 'Нет объяснения')} "
            f"| intent_score={result.get('intent_score')} "
            f"| niche_score={result.get('niche_score')} ",
            flush=True,
        )
        print("---------------", flush=True)

        if not result["lead"]:
            continue

        telegram_config = get_telegram_config_by_company(niche["company_id"])

        if not telegram_config:
            print(
                f"⚠️ Нет Telegram config для компании {niche['company_name']}",
                flush=True,
            )
            continue

        lead_result: LeadResult = {
            "lead_result_id": result["lead_result_id"],
            "lead": result["lead"],
            "niche_score": result["niche_score"],
            "intent_score": result["intent_score"],
            "description": result["description"],
            "reply_author_relation": result["reply_author_relation"],

            "source_link": job["source_link"],
            "source_title": job["source_title"],
            "text": job["clean_text"],
            "reply_text": job["reply_text"],

            "sender_name": job["sender_name"],
            "sender_username": job["sender_username"],
            "sender_id": job["sender_id"],

            "user_id": result.get("user_id"),
            "user_link": result.get("user_link", "Нет ссылки"),
        }

        try:
            sent = await send_to_leads(
                lead_result["lead_result_id"],
                lead_result,
                telegram_config,
            )

            if not sent:
                print("⚠️ Лид найден, но не отправлен в чат лидов", flush=True)


        except Exception:

            print("❌ Ошибка при отправке лида:", flush=True)

            traceback.print_exc()


async def message_worker():
    print("👷 Message worker started", flush=True)

    while True:
        job = await message_queue.get()

        message_queue_size.set(
            message_queue.qsize()
        )

        try:
            print(
                f"⚙️ Обработка job. queue_size={message_queue.qsize()}",
                flush=True,
            )

            delay_seconds = (
                datetime.now(timezone.utc)
                - job["created_at"]
            ).total_seconds()

            message_processing_delay_seconds.observe(
                max(delay_seconds, 0)
            )

            await process_job(job)

        except Exception as e:
            print(
                f"❌ Ошибка в message_worker: {type(e).__name__}: {e}",
                flush=True,
            )

        finally:
            message_queue.task_done()

            message_queue_size.set(
                message_queue.qsize()
            )