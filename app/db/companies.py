from app.db.connection import get_connection


def get_report_companies() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                c.id,
                c.name
            FROM companies c

            JOIN telegram_configs tc
                ON tc.company_id = c.id

            WHERE c.is_active = TRUE
              AND tc.is_active = TRUE
              AND tc.chat_id IS NOT NULL

            ORDER BY c.name
            """
        ).fetchall()

    return [dict(row) for row in rows]


def get_company_by_id(company_id: int) -> dict | None:
    with get_connection() as conn:
        result = conn.execute(
            """
            SELECT tc.company_id,
                   tc.chat_id,
                   tc.metrics_topic_id,
                   c.name AS company_name
            FROM telegram_configs tc

                     JOIN companies c
                          ON c.id = tc.company_id

            WHERE tc.company_id = %s
              AND tc.is_active = TRUE
              AND c.is_active = TRUE
              AND tc.chat_id IS NOT NULL

            LIMIT 1
            """,
            (company_id,),
        ).fetchone()

    return result