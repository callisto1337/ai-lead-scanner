import asyncio

from app.queue import message_queue
from app.db.niches import get_active_niches
from app.db.telegram_configs import get_telegram_config_by_company
from app.bot.sender import send_to_leads
from app.sender_utils import enrich_sender_info
from app.lead_processor import process_message


async def process_job(job: dict):
    niches = get_active_niches()

    if not niches:
        print("⚠️ Нет активных ниш", flush=True)
        print("---------------", flush=True)
        return

    for niche in niches:
        print(
            f"🔎 Проверка ниши: {niche['company_name']} / {niche['name']}",
            flush=True,
        )

        result = await asyncio.to_thread(
            process_message,
            clean_text=job["clean_text"],
            message_id=job["message_id"],
            tg_chat_id=job["tg_chat_id"],
            tg_message_id=job["tg_message_id"],
            reply_tg_message_id=job["reply_tg_message_id"],
            reply_text=job.get("reply_text"),
            niche=niche,
        )

        if not result:
            print("---------------", flush=True)
            continue

        enrich_sender_info(result, job["sender"])

        result["link"] = job["source_link"]
        result["text"] = job["clean_text"]

        if result["lead"]:
            print("🔥 Найден лид", flush=True)
        else:
            print("❌ Нерелевантное сообщение", flush=True)

        print(
            f"🤖 Объяснение: {result.get('description', 'Нет объяснения')} "
            f"| score={result.get('score')} "
            f"| prompt={result.get('prompt_version')}",
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

        try:
            sent = await send_to_leads(
                result["lead_result_id"],
                result,
                [],
                telegram_config,
            )

            if not sent:
                print("⚠️ Лид найден, но не отправлен в чат лидов", flush=True)

        except Exception as e:
            print(
                f"❌ Ошибка при отправке лида: {type(e).__name__}: {e}",
                flush=True,
            )


async def message_worker():
    print("👷 Message worker started", flush=True)

    while True:
        job = await message_queue.get()

        try:
            print(
                f"⚙️ Обработка job. queue_size={message_queue.qsize()}",
                flush=True,
            )

            await process_job(job)

        except Exception as e:
            print(
                f"❌ Ошибка в message_worker: {type(e).__name__}: {e}",
                flush=True,
            )

        finally:
            message_queue.task_done()