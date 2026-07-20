from typing import cast

from app.db.connection import get_connection
from app.types import ReportCompany, CompanyId


def get_report_companies() -> list[ReportCompany]:
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

    return [
        {
            "id": CompanyId(row["id"]),
            "name": str(row["name"]),
        }
        for row in rows
    ]


def get_company_by_id(
    company_id: CompanyId,
) -> ReportCompany | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT
                tc.company_id,
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

    if row is None:
        return None

    return cast(ReportCompany, row)