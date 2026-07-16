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