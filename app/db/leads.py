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
    verdict: str,
    niche_match: str,
    intent_match: str,
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
                verdict,
                niche_match,
                intent_match
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT(message_id, niche_id)
            DO UPDATE SET
                ai_lead = EXCLUDED.ai_lead,
                description = EXCLUDED.description,
                prompt = EXCLUDED.prompt,
                raw_response = EXCLUDED.raw_response,
                updated_at = EXCLUDED.updated_at,
                verdict = EXCLUDED.verdict,
                niche_match = EXCLUDED.niche_match,
                intent_match = EXCLUDED.intent_match
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
                verdict,
                niche_match,
                intent_match,
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