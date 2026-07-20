from datetime import datetime, timezone

from app.db.connection import get_connection
from app.types import LeadResultId, NicheId, RatedBy


def now_utc():
    return datetime.now(timezone.utc)



def update_lead_feedback(
    lead_result_id: LeadResultId,
    feedback: str,
    human_lead: bool | None,
    rated_by: RatedBy,
) -> bool:
    rated_at = now_utc()

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT feedback, human_lead
            FROM lead_results
            WHERE id = %s
            """,
            (lead_result_id,),
        ).fetchone()

        if not row:
            return False

        conn.execute(
            """
            UPDATE lead_results
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
                rated_at,
                lead_result_id,
            ),
        )

        conn.execute(
            """
            INSERT INTO lead_feedback_events (
                lead_result_id,
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
                lead_result_id,
                row["feedback"],
                feedback,
                row["human_lead"],
                human_lead,
                rated_at,
                rated_by.get("id"),
                rated_by.get("username"),
                rated_by.get("name"),
                rated_at,
            ),
        )

        conn.commit()

    return True


def count_final_feedback_since(
    since: datetime,
    niche_id: NicheId | None = None,
) -> dict[str, int]:
    params: list[object] = [since]

    where_niche = ""

    if niche_id is not None:
        where_niche = "AND niche_id = %s"
        params.append(niche_id)

    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT
                feedback,
                COUNT(*) AS total
            FROM lead_results
            WHERE rated_at IS NOT NULL
              AND rated_at >= %s
              AND feedback IS NOT NULL
              {where_niche}
            GROUP BY feedback
            """,
            params,
        ).fetchall()

    return {
        str(row["feedback"]): int(row["total"])
        for row in rows
    }
