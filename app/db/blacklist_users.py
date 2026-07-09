from datetime import datetime, timezone

from app.db.connection import get_connection


def now():
    return datetime.now(timezone.utc)


def is_blacklisted(user_id: int | None) -> bool:
    if not user_id:
        return False

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT 1
            FROM blacklist_users
            WHERE user_id = %s
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()

    return row is not None


def add_blacklisted_user(
    user_id: int | None,
    reason: str = "manual",
    created_by: int | None = None,
) -> bool:
    if not user_id:
        return False

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO blacklist_users (
                user_id,
                created_at,
                created_by,
                reason
            )
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE
            SET
                reason = EXCLUDED.reason,
                created_by = COALESCE(EXCLUDED.created_by, blacklist_users.created_by)
            """,
            (
                user_id,
                now(),
                created_by,
                reason,
            ),
        )

    return True


def remove_blacklisted_user(user_id: int | None) -> bool:
    if not user_id:
        return False

    with get_connection() as conn:
        result = conn.execute(
            """
            DELETE FROM blacklist_users
            WHERE user_id = %s
            """,
            (user_id,),
        )

    return result.rowcount > 0


def get_blacklisted_user(user_id: int | None):
    if not user_id:
        return None

    with get_connection() as conn:
        return conn.execute(
            """
            SELECT
                id,
                user_id,
                created_at,
                created_by,
                reason
            FROM blacklist_users
            WHERE user_id = %s
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()


def list_blacklisted_users(limit: int = 100):
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT
                id,
                user_id,
                created_at,
                created_by,
                reason
            FROM blacklist_users
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (limit,),
        ).fetchall()