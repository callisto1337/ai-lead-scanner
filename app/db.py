from datetime import datetime, timezone
import uuid

import psycopg
from psycopg.rows import dict_row

from app.settings import DATABASE_URL
from app.utils import get_hash


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_connection():
    return psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row,
    )


def init_db():
    with get_connection() as conn:
        conn.execute(
            """
            CREATE EXTENSION IF NOT EXISTS vector;
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages 
            (
                id TEXT PRIMARY KEY,
                reply_to_id TEXT REFERENCES messages(id),
                tg_message_id BIGINT,
                tg_chat_id BIGINT,
                text TEXT NOT NULL,
                description TEXT,
                user_id BIGINT,
                user_link TEXT,
                source_link TEXT,
                ai_lead BOOLEAN NOT NULL DEFAULT TRUE,
                feedback TEXT,
                human_lead BOOLEAN,
                detected_at TIMESTAMPTZ NOT NULL,
                rated_at TIMESTAMPTZ,
                rated_by_id BIGINT,
                rated_by_username TEXT,
                rated_by_name TEXT,
                created_at TIMESTAMPTZ NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS message_feedback_events 
            (
                id BIGSERIAL PRIMARY KEY,
                message_id TEXT NOT NULL REFERENCES messages(id),
                previous_feedback TEXT,
                new_feedback TEXT NOT NULL,
                previous_human_lead BOOLEAN,
                new_human_lead BOOLEAN,
                rated_at TIMESTAMPTZ NOT NULL,
                rated_by_id BIGINT,
                rated_by_username TEXT,
                rated_by_name TEXT,
                created_at TIMESTAMPTZ NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS message_embeddings
            (
                id SERIAL PRIMARY KEY,
                message_id TEXT NOT NULL
                    REFERENCES messages (id)
                    ON DELETE CASCADE,
                embedding vector(384),
                model TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE (message_id, model)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS seen_messages
            (
                id SERIAL PRIMARY KEY,
                hash TEXT,
                normalized_text TEXT,
                created_at TIMESTAMPTZ NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS blacklist_users
            (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL UNIQUE,
                created_at TIMESTAMPTZ NOT NULL,
                created_by BIGINT,
                reason TEXT
            )
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_messages_detected_at
                ON messages(detected_at)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_messages_rated_at
                ON messages(rated_at)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_feedback_events_messages_id
                ON message_feedback_events(message_id)
            """
        )


def _db_to_bool(value):
    if value is None:
        return None

    return bool(value)


def _rater_from_row(row):
    if row["rated_by_id"] is None and not row["rated_by_username"] and not row["rated_by_name"]:
        return None

    if row["rated_by_username"]:
        text = f"@{row['rated_by_username']}"
    elif row["rated_by_name"]:
        text = f"{row['rated_by_name']} (ID: {row['rated_by_id']})"
    else:
        text = f"ID: {row['rated_by_id']}"

    return {
        "id": row["rated_by_id"],
        "username": row["rated_by_username"],
        "name": row["rated_by_name"],
        "text": text,
    }


def _message_from_row(row):
    message = {
        "id": row["id"],
        "text": row["text"],
        "tg_message_id": row["tg_message_id"],
        "reply_to_id": row["reply_to_id"],
        "tg_chat_id": row["tg_chat_id"],
        "description": row["description"] or "",
        "user_id": row["user_id"],
        "user_link": row["user_link"],
        "link": row["source_link"],
        "lead": _db_to_bool(row["ai_lead"]),
        "feedback": row["feedback"],
        "human_lead": _db_to_bool(row["human_lead"]),
        "rated_at": row["rated_at"].isoformat() if row["rated_at"] else None,
    }

    rater = _rater_from_row(row)
    if rater:
        message["rated_by"] = rater

    return message


def save_message(data, event):
    init_db()

    message_id = str(uuid.uuid4())[:8]
    now = now_iso()
    detected_at = data.get("detected_at") or data.get("created_at") or now
    rated_by = data.get("rated_by") or {}
    reply = event.message.reply_to
    reply_to_id = None
    tg_message_id = event.message.id
    tg_chat_id = event.chat_id

    if reply:
        reply_to_id = get_message_by_tg_id(reply.reply_to_msg_id)

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO messages (
                id,
                text,
                description,
                user_id,
                user_link,
                source_link,
                reply_to_id,
                tg_message_id,
                tg_chat_id,
                ai_lead,
                feedback,
                human_lead,
                detected_at,
                rated_at,
                rated_by_id,
                rated_by_username,
                rated_by_name,
                created_at,
                updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT(id) DO UPDATE SET
                text = EXCLUDED.text,
                description = EXCLUDED.description,
                user_id = EXCLUDED.user_id,
                user_link = EXCLUDED.user_link,
                source_link = EXCLUDED.source_link,
                reply_to_id = EXCLUDED.reply_to_id,
                tg_message_id = EXCLUDED.tg_message_id,
                tg_chat_id = EXCLUDED.tg_chat_id,
                ai_lead = EXCLUDED.ai_lead,
                feedback = EXCLUDED.feedback,
                human_lead = EXCLUDED.human_lead,
                rated_at = EXCLUDED.rated_at,
                rated_by_id = EXCLUDED.rated_by_id,
                rated_by_username = EXCLUDED.rated_by_username,
                rated_by_name = EXCLUDED.rated_by_name,
                updated_at = EXCLUDED.updated_at
            """,
            (
                message_id,
                data["text"],
                data.get("description"),
                data.get("user_id"),
                data.get("user_link"),
                data.get("link"),
                reply_to_id,
                tg_message_id,
                tg_chat_id,
                data.get("lead", True),
                data.get("feedback"),
                data.get("human_lead"),
                detected_at,
                data.get("rated_at"),
                rated_by.get("id"),
                rated_by.get("username"),
                rated_by.get("name"),
                now,
                now,
            )
        )

    return message_id


def update_message_feedback(message_id, feedback, human_lead, rated_at, rated_by):
    init_db()

    with get_connection() as conn:
        row = conn.execute(
            "SELECT feedback, human_lead FROM messages WHERE id = %s",
            (message_id,)
        ).fetchone()

        if not row:
            return False

        conn.execute(
            """
            UPDATE messages
            SET
                feedback = %s,
                human_lead = %s,
                rated_at = %s,
                rated_by_id = %s,
                rated_by_username = %s,
                rated_by_name = %s,
                updated_at = %s
            WHERE id = %s
            """,
            (
                feedback,
                human_lead,
                rated_at,
                rated_by.get("id"),
                rated_by.get("username"),
                rated_by.get("name"),
                now_iso(),
                message_id,
            )
        )

        conn.execute(
            """
            INSERT INTO message_feedback_events (
                message_id,
                previous_feedback,
                new_feedback,
                previous_human_lead,
                new_human_lead,
                rated_at,
                rated_by_id,
                rated_by_username,
                rated_by_name,
                created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                message_id,
                row["feedback"],
                feedback,
                row["human_lead"],
                human_lead,
                rated_at,
                rated_by.get("id"),
                rated_by.get("username"),
                rated_by.get("name"),
                now_iso(),
            )
        )

    return True


def count_final_feedback_since(since_iso):
    init_db()

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT feedback, COUNT(*) AS total
            FROM messages
            WHERE rated_at IS NOT NULL
              AND rated_at >= %s
            GROUP BY feedback
            """,
            (since_iso,)
        ).fetchall()

    return {
        row["feedback"]: row["total"]
        for row in rows
    }


def save_embedding(message_id, embedding):
    init_db()

    with get_connection() as conn:

        conn.execute(
            """
            INSERT INTO message_embeddings
            (
                message_id,
                embedding,
                model
            )
            VALUES (%s,%s,%s)

            ON CONFLICT(message_id, model)
            DO NOTHING
            """,
            (
                message_id,
                embedding,
                "paraphrase-multilingual-MiniLM-L12-v2"
            )
        )


def get_messages_without_embeddings(limit=10):
    init_db()

    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT m.*
            FROM messages m
            LEFT JOIN message_embeddings e
            ON e.message_id = m.id
            WHERE e.id IS NULL
            LIMIT {limit};
            """
        ).fetchall()

    return rows


def save_seen_message(normalized_text):
    init_db()

    msg_hash = get_hash(normalized_text)

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO seen_messages
            (
                hash,
                normalized_text,
                created_at
            )
            VALUES (%s, %s, %s)
            """,
            (
                msg_hash,
                normalized_text,
                datetime.now(timezone.utc)
            )
        )


def exists_seen_message(msg_hash: str) -> bool:
    init_db()

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT 1
            FROM seen_messages
            WHERE hash = %s
            LIMIT 1
            """,
            (msg_hash,)
        ).fetchone()

    return row is not None


def add_to_blacklist(
    user_id: int,
    created_by: int | None = None,
    reason: str = "spam"
):
    init_db()

    if not user_id:
        return

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO blacklist_users 
            (
                user_id,
                created_at,
                created_by,
                reason
            )
            VALUES (%s, %s, %s, %s)

            ON CONFLICT(user_id)
                DO NOTHING
            """,
            (
                user_id,
                datetime.now(timezone.utc),
                created_by,
                reason
            )
        )


def is_blacklisted(user_id: int) -> bool:
    init_db()

    if not user_id:
        return False

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT 1
            FROM blacklist_users
            WHERE user_id = %s
            """,
            (user_id,)
        ).fetchone()

    return row is not None


def remove_from_blacklist(user_id: int):
    init_db()

    if not user_id:
        return False

    with get_connection() as conn:
        result = conn.execute(
            """
            DELETE FROM blacklist_users
            WHERE user_id = %s
            """,
            (user_id,)
        )

    return result.rowcount > 0


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


def get_message_by_tg_id(tg_message_id: int):
    init_db()

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
                SELECT
                    text,
                    reply_to_id
                FROM messages
                WHERE id = %s
                """,
                (current_id,)
            ).fetchone()

            if not row:
                break

            chain.append(row["text"])
            current_id = row["reply_to_id"]

    chain.reverse()
    return chain


def get_reply_chain_from_tg_id(reply_to_tg_message_id: int, limit=3):
    parent = get_message_by_tg_id(reply_to_tg_message_id)

    if not parent:
        return []

    return get_reply_chain(parent["id"], limit)


def get_chat_history(
    tg_chat_id: int,
    before_tg_message_id: int,
    limit: int = 3
) -> list[str]:
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
            (
                tg_chat_id,
                before_tg_message_id,
                limit
            )
        ).fetchall()

    return [row["text"] for row in reversed(rows)]


def get_context_chain(
    tg_chat_id: int,
    tg_message_id: int,
    reply_to_tg_message_id: int | None,
    limit: int = 3,
) -> list[str]:
    if reply_to_tg_message_id:
        chain = get_reply_chain_from_tg_id(
            reply_to_tg_message_id,
            limit,
        )

        if chain:
            return chain

    return get_chat_history(
        tg_chat_id,
        tg_message_id,
        limit,
    )
