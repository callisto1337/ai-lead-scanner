from datetime import datetime, timezone
import uuid

from app.db.connection import get_connection
from app.types import TG_MESSAGE_ID, MESSAGE_ID


def now_utc():
    return datetime.now(timezone.utc)


def save_message(data, event):
    message_id = str(uuid.uuid4())[:8]

    reply = event.message.reply_to
    reply_to_id = None

    if reply:
        reply_row = get_message_by_tg_id(reply.reply_to_msg_id)
        reply_to_id = reply_row["id"] if reply_row else None

    current_time = now_utc()

    with get_connection() as conn:
        row = conn.execute(
            """
            INSERT INTO messages (
                id,
                reply_to_id,
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
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT(tg_chat_id, tg_message_id)
            DO UPDATE SET
                text = EXCLUDED.text,
                user_id = EXCLUDED.user_id,
                user_link = EXCLUDED.user_link,
                source_link = EXCLUDED.source_link,
                updated_at = EXCLUDED.updated_at
            RETURNING id
            """,
            (
                message_id,
                reply_to_id,
                event.message.id,
                event.chat_id,
                data["text"],
                data.get("user_id"),
                data.get("user_link"),
                data.get("link"),
                data.get("tg_created_at"),
                current_time,
                current_time,
            )
        ).fetchone()

        conn.commit()

    return row["id"]


def get_message_by_id(message_id: str):
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT * 
            FROM messages
            WHERE id = %s
            """,
            (message_id,)
        ).fetchone()


def get_message_by_tg_id(tg_message_id: TG_MESSAGE_ID | None):
    if not tg_message_id:
        return None

    with get_connection() as conn:
        return conn.execute(
            """
            SELECT *
            FROM messages
            WHERE tg_message_id = %s
            LIMIT 1
            """,
            (tg_message_id,)
        ).fetchone()


def get_reply_chain(message_id: str, limit: int = 3) -> list[str]:
    chain = []
    current_id = message_id

    with get_connection() as conn:
        while current_id and len(chain) < limit:
            row = conn.execute(
                """
                SELECT text, reply_to_id
                FROM messages
                WHERE id = %s
                """,
                (current_id,)
            ).fetchone()

            if not row:
                break

            chain.append(row["text"])
            current_id = row["reply_to_id"]

    return list(reversed(chain))


def get_chat_history(tg_chat_id: int, tg_message_id: int, limit: int = 3):
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT text
            FROM messages
            WHERE tg_chat_id = %s
              AND tg_message_id < %s
            ORDER BY tg_message_id DESC
            LIMIT %s
            """,
            (tg_chat_id, tg_message_id, limit)
        ).fetchall()

    return [r["text"] for r in reversed(rows)]


def get_context_chain(
    tg_chat_id: int,
    tg_message_id: TG_MESSAGE_ID,
    reply_to_id: MESSAGE_ID | None = None,
    limit: int = 3,
    message_id: MESSAGE_ID | None = None,
) -> list[str]:

    # 1. reply-chain (если есть связь)
    if reply_to_id:
        chain = get_reply_chain(reply_to_id, limit)

        if chain:
            return chain

    # 2. fallback: последние сообщения чата
    return get_chat_history(
        tg_chat_id,
        tg_message_id,
        limit
    )