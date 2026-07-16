from app.db.connection import get_connection


def has_recent_user_lead(
    *,
    user_id: int | None,
    niche_id: int,
    cooldown_minutes: int,
) -> bool:
    if user_id is None or cooldown_minutes <= 0:
        return False

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM lead_results lr

                JOIN messages m
                    ON m.id = lr.message_id

                WHERE m.user_id = %s
                  AND lr.niche_id = %s
                  AND lr.ai_lead = TRUE
                  AND lr.detected_at >= NOW() - (%s * INTERVAL '1 minute')
            ) AS exists
            """,
            (
                user_id,
                niche_id,
                cooldown_minutes,
            ),
        ).fetchone()

    return bool(row["exists"])