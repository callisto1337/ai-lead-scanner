from datetime import datetime
from typing import TypedDict, cast

from app.db.connection import get_connection
from app.types import NicheId, TgUserId


class ExistsRow(TypedDict):
    exists: bool


def has_recent_user_lead(
    *,
    user_id: TgUserId,
    niche_id: NicheId,
    message_created_at: datetime,
    cooldown_minutes: int,
) -> bool:
    if cooldown_minutes <= 0:
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
                  AND m.created_at < %s
                  AND m.created_at >= (
                      %s - (%s * INTERVAL '1 minute')
                  )
            ) AS exists
            """,
            (
                user_id,
                niche_id,
                message_created_at,
                message_created_at,
                cooldown_minutes,
            ),
        ).fetchone()

    if row is None:
        return False

    typed_row = cast(ExistsRow, row)

    return typed_row["exists"]