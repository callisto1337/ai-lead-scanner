from datetime import datetime, timezone
from typing import Any, cast

from psycopg.types.json import Jsonb

from app.db.connection import get_connection
from app.types import LeadResultId, TgUserId, MessageId, NicheId, SavedLeadResult


def now_utc():
    return datetime.now(timezone.utc)


def save_lead_result(
    message_id: MessageId,
    niche_id: NicheId,
    ai_lead: bool,
    description: str,
    niche_score: int,
    intent_score: int,
    prompt: str | None = None,
    raw_response: dict[str, Any] | None = None,
) -> SavedLeadResult | None:
    current_time = now_utc()

    with get_connection() as conn:
        row = conn.execute(
            """
            INSERT INTO lead_results (
                message_id,
                niche_id,
                ai_lead,
                description,
                prompt,
                raw_response,
                detected_at,
                created_at,
                updated_at,
                niche_score,
                intent_score
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT(message_id, niche_id)
            DO UPDATE SET
                ai_lead = EXCLUDED.ai_lead,
                description = EXCLUDED.description,
                prompt = EXCLUDED.prompt,
                raw_response = EXCLUDED.raw_response,
                updated_at = EXCLUDED.updated_at,
                niche_score = EXCLUDED.niche_score,
                intent_score = EXCLUDED.intent_score
            RETURNING *
            """,
            (
                message_id,
                niche_id,
                ai_lead,
                description,
                prompt,
                Jsonb(raw_response) if raw_response is not None else None,
                current_time,
                current_time,
                current_time,
                niche_score,
                intent_score
            )
        ).fetchone()

        conn.commit()

    return cast(SavedLeadResult | None, row)


def get_user_id_by_lead_result_id(lead_result_id: LeadResultId) -> TgUserId | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT m.user_id
            FROM lead_results lr
            JOIN messages m
                ON m.id = lr.message_id
            WHERE lr.id = %s
            LIMIT 1
            """,
            (lead_result_id,),
        ).fetchone()

    if not row:
        return None

    return row["user_id"]