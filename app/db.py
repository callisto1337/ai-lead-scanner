from datetime import datetime, timezone

import psycopg
from psycopg.rows import dict_row

from app.settings import DATABASE_URL


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
            CREATE TABLE IF NOT EXISTS leads (
                id TEXT PRIMARY KEY,
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
            CREATE TABLE IF NOT EXISTS lead_feedback_events (
                id BIGSERIAL PRIMARY KEY,
                lead_id TEXT NOT NULL REFERENCES leads(id),
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
            CREATE INDEX IF NOT EXISTS idx_leads_detected_at
                ON leads(detected_at)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_leads_rated_at
                ON leads(rated_at)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_feedback_events_lead_id
                ON lead_feedback_events(lead_id)
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


def _lead_from_row(row):
    lead = {
        "id": row["id"],
        "text": row["text"],
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
        lead["rated_by"] = rater

    return lead


def save_lead(lead_id, data):
    init_db()

    now = now_iso()
    detected_at = data.get("detected_at") or data.get("created_at") or now
    rated_by = data.get("rated_by") or {}

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO leads (
                id,
                text,
                description,
                user_id,
                user_link,
                source_link,
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
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT(id) DO UPDATE SET
                text = EXCLUDED.text,
                description = EXCLUDED.description,
                user_id = EXCLUDED.user_id,
                user_link = EXCLUDED.user_link,
                source_link = EXCLUDED.source_link,
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
                lead_id,
                data["text"],
                data.get("description"),
                data.get("user_id"),
                data.get("user_link"),
                data.get("link"),
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


def get_lead(lead_id):
    init_db()

    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM leads WHERE id = %s",
            (lead_id,)
        ).fetchone()

    if not row:
        return None

    return _lead_from_row(row)


def update_lead_feedback(lead_id, feedback, human_lead, rated_at, rated_by):
    init_db()

    with get_connection() as conn:
        row = conn.execute(
            "SELECT feedback, human_lead FROM leads WHERE id = %s",
            (lead_id,)
        ).fetchone()

        if not row:
            return False

        conn.execute(
            """
            UPDATE leads
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
                lead_id,
            )
        )

        conn.execute(
            """
            INSERT INTO lead_feedback_events (
                lead_id,
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
                lead_id,
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
            FROM leads
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
