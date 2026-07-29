import uuid

from datetime import datetime, timezone

from app.db.connection import get_connection
from app.types import TgMessageId, MessageId, TgChatId, NewMessageEvent, MessageData, TgUserId


def now_utc():
    return datetime.now(timezone.utc)


def save_message(
    data: MessageData,
    event: NewMessageEvent,
) -> MessageId:
    chat_id = event.chat_id

    if chat_id is None:
        raise ValueError("У сообщения отсутствует chat_id")

    tg_chat_id = TgChatId(chat_id)
    tg_message_id = TgMessageId(event.message.id)

    message_id = MessageId(str(uuid.uuid4())[:8])

    reply_to_id: MessageId | None = None
    reply_sender_id: TgUserId | None = None

    reply = event.message.reply_to

    if reply is not None:
        reply_to_msg_id = reply.reply_to_msg_id

        if reply_to_msg_id is not None:
            reply_row = get_message_by_tg_id(
                tg_chat_id=tg_chat_id,
                tg_message_id=TgMessageId(reply_to_msg_id),
            )

            if reply_row is not None:
                reply_to_id = MessageId(reply_row["id"])

                raw_reply_sender_id = reply_row["user_id"]

                if raw_reply_sender_id is not None:
                    reply_sender_id = TgUserId(raw_reply_sender_id)

    current_time = now_utc()

    with get_connection() as conn:
        row = conn.execute(
            """
            INSERT INTO messages (
                id,
                reply_to_id,
                reply_sender_id,
                tg_message_id,
                tg_chat_id,
                text,
                user_id,
                user_link,
                source_link,
                tg_created_at,
                created_at,
                updated_at
            )
            VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (tg_chat_id, tg_message_id)
            DO UPDATE SET
                reply_to_id = EXCLUDED.reply_to_id,
                reply_sender_id = EXCLUDED.reply_sender_id,
                text = EXCLUDED.text,
                user_id = EXCLUDED.user_id,
                user_link = EXCLUDED.user_link,
                source_link = EXCLUDED.source_link,
                tg_created_at = EXCLUDED.tg_created_at,
                updated_at = EXCLUDED.updated_at
            RETURNING id
            """,
            (
                message_id,
                reply_to_id,
                reply_sender_id,
                tg_message_id,
                tg_chat_id,
                data["text"],
                data["user_id"],
                data["user_link"],
                data["link"],
                data["tg_created_at"],
                current_time,
                current_time,
            ),
        ).fetchone()

        conn.commit()

    if row is None:
        raise RuntimeError("Не удалось сохранить сообщение")

    raw_id = row["id"]

    if not isinstance(raw_id, str):
        raise TypeError("База данных вернула некорректный id сообщения")

    return MessageId(raw_id)


def get_message_by_id(message_id: MessageId):
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT * 
            FROM messages
            WHERE id = %s
            """,
            (message_id,)
        ).fetchone()


def get_message_by_tg_id(
    tg_chat_id: TgChatId,
    tg_message_id: TgMessageId | None,
):
    if not tg_message_id:
        return None

    with get_connection() as conn:
        return conn.execute(
            """
            SELECT *
            FROM messages
            WHERE tg_chat_id = %s
              AND tg_message_id = %s
            LIMIT 1
            """,
            (
                tg_chat_id,
                tg_message_id,
            ),
        ).fetchone()
