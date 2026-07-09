from telethon import events

from app.db.messages import save_message, get_context_chain
from app.db.blacklist_users import is_blacklisted
from app.db.dedup import save_seen_message
from app.db.niches import get_active_niches
from app.metrics import spam_detected
from app.prefilter import prefilter_message
from app.bot.sender import send_to_leads
from app.utils import build_tg_link, normalize
from app.sender_utils import enrich_sender_info
from app.lead_processor import process_message
from app.db.telegram_configs import get_telegram_config_by_company


def register_handlers(client):
    @client.on(events.NewMessage())
    async def handler(event):
        await handle_new_message(event)


async def handle_new_message(event):
    if event.out:
        return

    if event.message.post:
        print("⏭️ Пропуск поста канала")
        return

    sender = await event.get_sender()

    if sender and getattr(sender, "bot", False):
        return

    if sender and is_blacklisted(sender.id):
        print("⛔ BLACKLIST USER:", sender.id, flush=True)
        return

    text = event.message.text or ""
    clean_text = normalize(text)

    if not clean_text:
        return

    short_text = clean_text[:150] + "..." if len(clean_text) > 150 else clean_text
    print("💬 Новое сообщение:", short_text, flush=True)

    # Глобальный prefilter: дубль / мусор / общий спам.
    # Должен выполняться один раз на сообщение, а не на каждую нишу.
    prefilter_result = prefilter_message(clean_text)

    if not prefilter_result["ok"]:
        spam_detected.inc()
        print(f"❌ {prefilter_result['reason']}", flush=True)
        print("---------------", flush=True)
        return

    # Сохраняем как увиденное только после успешного prefilter.
    save_seen_message(clean_text)

    if event.message.reply_to_msg_id:
        reply = await event.get_reply_message()
    else:
        reply = None

    source_link = await build_tg_link(event)

    message_id = save_message(
        {
            "text": clean_text,
            "user_id": sender.id if sender else None,
            "link": source_link,
            "tg_created_at": event.message.date,
        },
        event,
    )

    context = get_context_chain(
        tg_chat_id=event.chat_id,
        tg_message_id=event.message.id,
        message_id=message_id,
    )

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

        result = process_message(
            clean_text=clean_text,
            message_id=message_id,
            tg_chat_id=event.chat_id,
            tg_message_id=event.message.id,
            reply_tg_message_id=reply.id if reply else None,
            niche=niche,
        )

        if not result:
            print("---------------", flush=True)
            continue

        enrich_sender_info(result, sender)

        result["link"] = source_link
        result["text"] = clean_text

        if result["lead"]:
            print("🔥 Найден лид", flush=True)
        else:
            print("❌ Нерелевантное сообщение", flush=True)

        print(
            "🤖 Объяснение:",
            result.get("description", "Нет объяснения"),
            flush=True,
        )

        print("---------------", flush=True)

        if not result["lead"]:
            continue

        telegram_config = get_telegram_config_by_company(niche["company_id"])

        if not telegram_config:
            print(
                f"⚠️ Нет Telegram config для компании {niche['company_name']}",
                f"---------------",
                flush=True,
            )
            continue

        try:
            print(
                f"📤 Отправляем лид lead_result_id={result['lead_result_id']} "
                f"chat_id={telegram_config.get('chat_id')} "
                f"leads_topic_id={telegram_config.get('leads_topic_id')}",
                f"---------------",
                flush=True,
            )

            sent = await send_to_leads(
                result["lead_result_id"],
                result,
                context,
                telegram_config,
            )

            if not sent:
                print("⚠️ Лид найден, но не отправлен в чат лидов", flush=True)

        except Exception as e:
            print(f"❌ Ошибка при отправке лида: {e}", flush=True)