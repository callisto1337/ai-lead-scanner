from telethon import events
from bot import send_to_leads, LEADS_CHAT_ID
from utils import build_tg_link
from blacklist import is_blacklisted
from sender_utils import enrich_sender_info
from lead_processor import process_message


def register_handlers(client):
    @client.on(events.NewMessage())
    async def handler(event):
        await handle_new_message(event)


async def handle_new_message(event):
    if event.out:
        return

    if event.chat_id == LEADS_CHAT_ID:
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
    clean_text = text.strip()
    short_text = clean_text[:100] + "..." if len(clean_text) > 100 else clean_text

    if not clean_text:
        return

    print("💬 Новое сообщение:", short_text, flush=True)

    result = process_message(clean_text)

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
            sent = await send_to_leads(
                result,
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
