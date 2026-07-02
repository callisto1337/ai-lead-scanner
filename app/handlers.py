from telethon import events
from app.db import save_seen_message, save_message, is_blacklisted
from app.settings import CHAT_ID
from app.bot.sender import send_to_leads
from app.utils import build_tg_link, normalize
from app.sender_utils import enrich_sender_info
from app.lead_processor import process_message


def register_handlers(client):
    @client.on(events.NewMessage())
    async def handler(event):
        await handle_new_message(event)


async def handle_new_message(event):
    if event.out:
        return

    # Чат, куда бот шлет сообщения
    if event.chat_id == CHAT_ID:
        return

    # Сообщение отправлено от имени канала/группы
    if event.message.post:
        print("⏭️ Пропуск поста канала")
        return

    sender = await event.get_sender()

    if sender and getattr(sender, "bot", False):
        return

    if sender and is_blacklisted(sender.id):
        print(
            "⛔ BLACKLIST USER:",
            sender.id,
            flush=True
        )
        return

    text = event.message.text or ""
    clean_text = normalize(text)
    short_text = clean_text[:150] + "..." if len(clean_text) > 150 else clean_text

    if not clean_text:
        return

    print("💬 Новое сообщение:", short_text, flush=True)

    if event.message.reply_to_msg_id:
        reply = await event.get_reply_message()
    else:
        reply = None

    reply_text = None

    if reply:
        reply_text = normalize(reply.raw_text)
        print("💬 Reply:", reply_text, flush=True)

    result = process_message(
        clean_text,
        reply_text
    )

    save_seen_message(clean_text)

    if not result:
        print("---------------", flush=True)
        return

    enrich_sender_info(result, sender)

    if result["lead"]:
        print("🔥 Найден лид", flush=True)
    else:
        print("❌ Нерелевантное сообщение", flush=True)

    print("🤖 Объяснение:", result.get("description", "Нет объяснения"), flush=True)
    print("---------------", flush=True)

    if result["lead"]:
        result["link"] = await build_tg_link(event)

        try:
            message_id = save_message(result)
            sent = await send_to_leads(
                message_id,
                result,
                reply_text
            )

            if not sent:
                print(
                    "⚠️ Лид найден, но не отправлен в чат лидов",
                    flush=True
                )

        except Exception as e:
            print(
                f"❌ Ошибка при отправке лида: {e}",
                flush=True
            )
