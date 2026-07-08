from . import get_connection


def add_to_blacklist(
    user_id: int,
    created_by: int | None = None,
    reason: str = "spam"
):
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