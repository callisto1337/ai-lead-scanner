import asyncio

from telethon import events  # pyright: ignore[reportMissingTypeStubs]

from app.db.blacklist_users import is_blacklisted
from app.db.dedup import save_seen_message
from app.db.messages import save_message
from app.metrics import spam_detected, message_queue_size, prefilter_rejected_total, prefilter_passed_total
from app.prefilter import prefilter_message
from app.queue import message_queue
from app.types import (
    MessageData,
    MessageQueueItem,
    NewMessageEvent,
    TelegramClientProtocol,
    TgChatId,
    TgMessageId,
    TgUser,
    TgUserId,
)
from app.utils import build_tg_link, normalize


def register_handlers(client: TelegramClientProtocol) -> None:
    @client.on(events.NewMessage())
    async def handler(  # pyright: ignore[reportUnusedFunction]
        event: NewMessageEvent,
    ) -> None:
        await handle_new_message(event)


async def handle_new_message(
    event: NewMessageEvent,
) -> None:
    if event.out:
        return

    if event.message.post:
        print("⏭️ Пропуск поста канала", flush=True)
        return

    chat_id = event.chat_id

    if chat_id is None:
        return

    tg_chat_id = TgChatId(chat_id)

    sender = await event.get_sender()

    if sender is not None and sender.bot:
        return

    sender_id: TgUserId | None = (
        TgUserId(sender.id)
        if sender is not None
        else None
    )

    sender_name: str | None = None
    sender_username: str | None = None
    sender_data: TgUser | None = None

    if sender is not None:
        sender_name = " ".join(
            part
            for part in (
                sender.first_name,
                sender.last_name,
            )
            if part is not None
        ).strip() or None

        sender_username = sender.username

        sender_data = TgUser(
            id=TgUserId(sender.id),
            bot=sender.bot,
            first_name=sender.first_name,
            last_name=sender.last_name,
            username=sender.username,
        )

    sender_username: str | None = (
        sender.username
        if sender is not None
        else None
    )

    if sender_id is not None and is_blacklisted(sender_id):
        print("⛔ BLACKLIST USER:", sender_id, flush=True)
        return

    text = event.message.text or ""
    reply_to_msg_id = event.message.reply_to_msg_id or ""
    clean_text = normalize(text)

    if not clean_text:
        return

    short_text = (
        clean_text[:150] + "..."
        if len(clean_text) > 150
        else clean_text
    )

    print("💬 Новое сообщение:", short_text, flush=True)

    prefilter_result = prefilter_message(
        clean_text,
        has_reply=True if reply_to_msg_id else False,
    )

    if not prefilter_result["ok"]:
        spam_detected.inc()

        prefilter_rejected_total.labels(
            reason=prefilter_result["reason"],
        ).inc()

        print(
            f"❌ {prefilter_result['reason']}",
            flush=True,
        )
        print("---------------", flush=True)
        return

    prefilter_passed_total.inc()

    save_seen_message(clean_text)

    reply_text: str | None = None
    reply_sender_id: TgUserId | None = None
    reply_tg_message_id: TgMessageId | None = None

    if event.message.reply_to_msg_id is not None:
        reply = await event.get_reply_message()

        if reply is not None:
            reply_tg_message_id = TgMessageId(reply.id)

            if reply.sender_id is not None:
                reply_sender_id = TgUserId(reply.sender_id)

            if reply.text:
                reply_text = reply.text.strip()

    chat = await event.get_chat()
    source_link = await build_tg_link(event)

    source_title = (
        getattr(chat, "title", None)
        or getattr(chat, "username", None)
        or getattr(chat, "first_name", None)
        or "Открыть источник"
    )

    message_data: MessageData = {
        "text": clean_text,
        "user_id": sender_id,
        "user_link": None,
        "link": source_link,
        "tg_created_at": event.message.date,
    }

    message_id = save_message(
        message_data,
        event,
    )

    queue_item: MessageQueueItem = {
        "clean_text": clean_text,
        "message_id": message_id,
        "tg_chat_id": tg_chat_id,
        "tg_message_id": TgMessageId(event.message.id),
        "reply_tg_message_id": reply_tg_message_id,
        "reply_text": reply_text,
        "reply_sender_id": reply_sender_id,
        "source_link": source_link,
        "source_title": source_title,
        "sender_id": sender_id,
        "sender_name": sender_name,
        "sender_username": sender_username,
        "sender": sender_data,
        "created_at": message_data["tg_created_at"],
    }

    try:
        message_queue.put_nowait(queue_item)

        message_queue_size.set(
            message_queue.qsize()
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