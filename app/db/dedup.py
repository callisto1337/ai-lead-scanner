from datetime import datetime, timezone

from app.db.connection import get_connection
from app.utils import get_hash


def save_seen_message(normalized_text: str):
    msg_hash = get_hash(normalized_text)

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO seen_messages (
                hash,
                normalized_text,
                created_at
            )
            VALUES (%s, %s, %s)
            """,
            (
                msg_hash,
                normalized_text,
                datetime.now(timezone.utc),
            )
        )

        conn.commit()


def exists_seen_message(msg_hash: str) -> bool:
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