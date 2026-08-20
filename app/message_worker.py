import asyncio
import random
import traceback
from datetime import datetime, timezone

from app.db.chat_priority import get_chat_niche_sample_rate
from app.db.lead_results import has_recent_user_lead
from app.embeddings import create_embedding
from app.filter import classify_message_for_niches
from app.metrics import (
    chat_priority_skipped,
    user_lead_cooldown_skipped,
    message_queue_size,
    message_processing_delay_seconds,
)
from app.prefilter import prefilter_niche_message
from app.queue import message_queue
from app.db.niches import get_active_niches_with_config
from app.db.telegram_configs import get_telegram_config_by_company
from app.bot.sender import send_to_leads
from app.sender_utils import enrich_sender_info
from app.lead_processor import save_classification_result
from app.settings import CHAT_PRIORITY_ENABLED, USER_LEAD_COOLDOWN_MINUTES
from app.types import (
    IsLeadResult,
    LeadResult,
    MessageQueueItem,
    NicheWithConfig,
    ProcessMessageResult,
)


async def gate_niche(
    job: MessageQueueItem,
    niche: NicheWithConfig,
) -> bool:
    """
    Проверки, не требующие обращения к ИИ (свои для каждой ниши):
    blacklist конкретной ниши, cooldown по отправителю и приоритизация
    по (нише, чату). Возвращает True, если сообщение для этой ниши
    стоит классифицировать.
    """
    niche_prefilter_result = prefilter_niche_message(
        text=job["clean_text"],
        reply_text=job["reply_text"],
        niche_stopwords=niche.get("blacklist") or [],
    )

    if not niche_prefilter_result["ok"]:
        print(
            (
                "⛔ Пропуск ниши по blacklist: "
                f"company_id={niche['company_id']}, "
                f"niche_id={niche['id']}, "
                f"reason={niche_prefilter_result['reason']}"
            ),
            flush=True,
        )
        print("---------------", flush=True)

        return False

    sender_id = job["sender_id"]
    has_recent_lead = has_recent_user_lead(
        user_id=sender_id,
        niche_id=niche["id"],
        message_created_at=job["created_at"],
        cooldown_minutes=USER_LEAD_COOLDOWN_MINUTES,
    )

    if sender_id is not None and has_recent_lead:
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

        return False

    if CHAT_PRIORITY_ENABLED:
        sample_rate = get_chat_niche_sample_rate(
            niche["id"],
            job["tg_chat_id"],
        )

        if random.random() > sample_rate:
            chat_priority_skipped.labels(
                company_id=str(niche["company_id"]),
                niche_id=str(niche["id"]),
            ).inc()

            print(
                (
                    "🎯 Пропуск по приоритизации чата: "
                    f"company_id={niche['company_id']}, "
                    f"niche_id={niche['id']}, "
                    f"tg_chat_id={job['tg_chat_id']}, "
                    f"sample_rate={sample_rate:.3f}"
                ),
                flush=True,
            )

            return False

    return True


async def finalize_niche_result(
    job: MessageQueueItem,
    niche: NicheWithConfig,
    ai_result: IsLeadResult | None,
) -> None:
    if ai_result is None:
        print(
            f"❌ Классификация не удалась: niche_id={niche['id']}",
            flush=True,
        )
        print("---------------", flush=True)

        return

    result: ProcessMessageResult = save_classification_result(
        ai_result=ai_result,
        message_id=job["message_id"],
        niche=niche,
        sender_id=job["sender_id"],
        sender_name=job["sender_name"],
        sender_username=job["sender_username"],
    )

    enrich_sender_info(result, job["sender"])

    result["source_link"] = job["source_link"]
    result["source_title"] = job["source_title"]
    result["text"] = job["clean_text"]
    result["reply_text"] = job["reply_text"]

    if result["verdict"] == "lead":
        print("🔥 Найден лид", flush=True)
    elif result["verdict"] == "borderline":
        print("❓ Спорный лид", flush=True)
    else:
        print("❌ Нерелевантное сообщение", flush=True)

    print(
        f"🤖 Объяснение: {result.get('description', 'Нет объяснения')} "
        f"| intent_match={result.get('intent_match')} "
        f"| niche_match={result.get('niche_match')} ",
        flush=True,
    )
    print("---------------", flush=True)

    if not result["lead"]:
        return

    telegram_config = get_telegram_config_by_company(niche["company_id"])

    if not telegram_config:
        print(
            f"⚠️ Нет Telegram config для компании {niche['company_name']}",
            flush=True,
        )
        return

    lead_result: LeadResult = {
        "lead_result_id": result["lead_result_id"],
        "lead": result["lead"],
        "verdict": result["verdict"],
        "niche_match": result["niche_match"],
        "intent_match": result["intent_match"],
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


async def process_job(job: MessageQueueItem):
    niches = get_active_niches_with_config()

    if not niches:
        print("⚠️ Нет активных ниш", flush=True)
        print("---------------", flush=True)
        return

    await asyncio.to_thread(create_embedding, job["clean_text"])

    # Проверки без ИИ (blacklist ниши, cooldown) — свои на каждую
    # нишу, дешёвые, идут параллельно.
    gate_results = await asyncio.gather(
        *(gate_niche(job, niche) for niche in niches),
        return_exceptions=True,
    )

    eligible_niches: list[NicheWithConfig] = []

    for niche, gate_result in zip(niches, gate_results):
        if isinstance(gate_result, BaseException):
            print(
                (
                    f"❌ Ошибка проверки ниши "
                    f"niche_id={niche['id']}: "
                    f"{type(gate_result).__name__}: {gate_result}"
                ),
                flush=True,
            )
            continue

        if gate_result:
            eligible_niches.append(niche)

    if not eligible_niches:
        return

    # Классификация — ОДНА на сообщение, а не на нишу: extraction и
    # intent общие для всех прошедших проверку ниш (см.
    # app.filter.classify_message_for_niches), niche-match — свой на
    # каждую нишу.
    try:
        results_by_niche_id = await asyncio.to_thread(
            classify_message_for_niches,
            text=job["clean_text"],
            niches=eligible_niches,
            sender_id=job["sender_id"],
            reply_text=job["reply_text"],
            reply_sender_id=job["reply_sender_id"],
        )
    except Exception as error:
        print(
            f"❌ classify_message_for_niches упал: {type(error).__name__}: {error}",
            flush=True,
        )
        traceback.print_exc()
        return

    finalize_results = await asyncio.gather(
        *(
            finalize_niche_result(
                job, niche, results_by_niche_id.get(int(niche["id"]))
            )
            for niche in eligible_niches
        ),
        return_exceptions=True,
    )

    for niche, finalize_result in zip(eligible_niches, finalize_results):
        if isinstance(finalize_result, BaseException):
            print(
                (
                    f"❌ Ошибка обработки результата ниши "
                    f"niche_id={niche['id']}: "
                    f"{type(finalize_result).__name__}: {finalize_result}"
                ),
                flush=True,
            )


async def message_worker(
    worker_id: int,
) -> None:
    print(
        f"👷 Message worker #{worker_id} started",
        flush=True,
    )

    while True:
        job = await message_queue.get()

        message_queue_size.set(
            message_queue.qsize()
        )

        try:
            print(
                (
                    f"⚙️ Worker #{worker_id}: обработка job. "
                    f"queue_size={message_queue.qsize()}"
                ),
                flush=True,
            )

            delay_seconds = (
                datetime.now(timezone.utc)
                - job["enqueued_at"]
            ).total_seconds()

            message_processing_delay_seconds.observe(
                max(delay_seconds, 0)
            )

            await process_job(job)

        except Exception as e:
            print(
                (
                    f"❌ Ошибка в message_worker #{worker_id}: "
                    f"{type(e).__name__}: {e}"
                ),
                flush=True,
            )

        finally:
            message_queue.task_done()

            message_queue_size.set(
                message_queue.qsize()
            )
