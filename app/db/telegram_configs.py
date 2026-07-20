from typing import cast

from app.db.connection import get_connection
from app.types import CompanyId, TgConfig


def get_telegram_config_by_company(
    company_id: CompanyId,
) -> TgConfig | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM telegram_configs
            WHERE company_id = %s
              AND is_active = TRUE
            LIMIT 1
            """,
            (company_id,),
        ).fetchone()

    return cast(TgConfig | None, row)


def get_active_telegram_configs() -> list[TgConfig]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                tc.*,
                c.name AS company_name
            FROM telegram_configs tc
            JOIN companies c
                ON c.id = tc.company_id
            WHERE tc.is_active = TRUE
              AND c.is_active = TRUE
            ORDER BY c.id
            """
        ).fetchall()

    return cast(list[TgConfig], rows)