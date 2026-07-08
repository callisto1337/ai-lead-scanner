from datetime import datetime, timezone
from psycopg.types.json import Jsonb

from app.db.connection import get_connection


def now_utc():
    return datetime.now(timezone.utc)


def save_lead_result(
    message_id: str,
    niche_id: int,
    ai_lead: bool,
    description: str,
    prompt: str | None = None,
    raw_response: dict | None = None,
):
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
                updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT(message_id, niche_id)
            DO UPDATE SET
                ai_lead = EXCLUDED.ai_lead,
                description = EXCLUDED.description,
                prompt = EXCLUDED.prompt,
                raw_response = EXCLUDED.raw_response,
                updated_at = EXCLUDED.updated_at
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
            )
        ).fetchone()

        conn.commit()

    return row