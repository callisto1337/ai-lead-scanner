import asyncio
from datetime import datetime, timezone

from telethon import events  # pyright: ignore[reportMissingTypeStubs]

from app.db.blacklist_users import is_blacklisted
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
from app.watchdog import mark_event_received


def register_handlers(client: TelegramClientProtocol) -> None:
    @client.on(events.NewMessage())
    async def handler(  # pyright: ignore[reportUnusedFunction]
        event: NewMessageEvent,
    ) -> None:
        mark_event_received()
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

    # get_sender() может вернуть Channel (пост от имени канала,
    # анонимный админ) вместо User — у Channel нет .bot/.first_name/
    # .last_name, поэтому дальше везде читаем через getattr().
    if sender is not None and getattr(sender, "bot", False):
        return

    sender_id = (
        TgUserId(sender.id)
        if sender is not None
        else None
    )

    sender_name: str | None = None
    sender_username: str | None = None
    sender_data: TgUser | None = None

    if sender is not None:
        sender_first_name = getattr(sender, "first_name", None)
        sender_last_name = getattr(sender, "last_name", None)

        sender_name = " ".join(
            part
            for part in (
                sender_first_name,
                sender_last_name,
            )
            if part is not None
        ).strip() or getattr(sender, "title", None)

        sender_username = getattr(sender, "username", None)

        sender_data = TgUser(
            id=TgUserId(sender.id),
            bot=getattr(sender, "bot", False),
            first_name=sender_first_name,
            last_name=sender_last_name,
            username=sender_username,
        )

    if sender_id is not None and is_blacklisted(sender_id):
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

    prefilter_result = prefilter_message(
        clean_text
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
        "enqueued_at": datetime.now(timezone.utc),
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