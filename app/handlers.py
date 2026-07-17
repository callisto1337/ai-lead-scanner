import asyncio

from telethon import events

from app.db.messages import save_message
from app.db.blacklist_users import is_blacklisted
from app.db.dedup import save_seen_message
from app.metrics import spam_detected
from app.prefilter import prefilter_message
from app.utils import build_tg_link, normalize
from app.queue import message_queue


def register_handlers(client):
    @client.on(events.NewMessage())
    async def handler(event):
        await handle_new_message(event)


async def handle_new_message(event):
    if event.out:
        return

    if event.message.post:
        print("⏭️ Пропуск поста канала", flush=True)
        return

    sender = await event.get_sender()

    if sender and getattr(sender, "bot", False):
        return

    sender_id = sender.id if sender else None
    sender_name = getattr(sender, "firstname", None)
    sender_username = getattr(sender, "username", None)

    if sender_id and is_blacklisted(sender_id):
        print("⛔ BLACKLIST USER:", sender_id, flush=True)
        return

    text = event.message.text or ""
    clean_text = normalize(text)

    if not clean_text:
        return

    short_text = (
        clean_text[:150] + "..."
        if len(clean_text) > 150
        else clean_text
    )

    print("💬 Новое сообщение:", short_text, flush=True)

    prefilter_result = prefilter_message(clean_text)

    if not prefilter_result["ok"]:
        spam_detected.inc()

        print(
            f"❌ {prefilter_result['reason']}",
            flush=True,
        )
        print("---------------", flush=True)
        return

    save_seen_message(clean_text)

    reply_text = None
    reply_sender_id = None
    reply_tg_message_id = None

    if event.message.reply_to_msg_id:
        reply = await event.get_reply_message()

        if reply:
            reply_tg_message_id = reply.id
            reply_sender_id = reply.sender_id

            if reply.text:
                reply_text = reply.text.strip()

    chat = await event.get_chat()
    source_link = await build_tg_link(event)
    source_title = (
        getattr(chat, "title", None)
        or getattr(chat, "username", None)
        or "Открыть источник"
    )
    message_id = save_message(
        {
            "text": clean_text,
            "user_id": sender_id,
            "link": source_link,
            "tg_created_at": event.message.date,
            "reply_sender_id": reply_sender_id,
        },
        event,
    )

    try:
        message_queue.put_nowait(
            {
                "clean_text": clean_text,
                "message_id": message_id,
                "tg_chat_id": event.chat_id,
                "tg_message_id": event.message.id,
                "reply_tg_message_id": reply_tg_message_id,
                "reply_text": reply_text,
                "reply_sender_id": reply_sender_id,
                "source_link": source_link,
                "source_title": source_title,
                "sender_id": sender_id,
                "sender_name": sender_name,
                "sender_username": sender_username,
                "sender": sender,
            }
        )

        print(
            (
                "📥 Сообщение добавлено в очередь. "
                f"queue_size={message_queue.qsize()}"
            ),
            flush=True,
        )

    except asyncio.QueueFull:
        print(
            "⚠️ Очередь AI заполнена, сообщение пропущено",
            flush=True,
        )
        return