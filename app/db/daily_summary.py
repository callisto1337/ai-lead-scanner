from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import cast
from zoneinfo import ZoneInfo

from app.db.connection import get_connection
from app.types import CompanyId, TgChatId, SummaryTarget, NicheId, DailySummaryStats, DailySummaryRow

MOSCOW_TZ = ZoneInfo("Europe/Moscow")


def get_daily_summary_stats(
    company_id: CompanyId,
    started_at: datetime,
    ended_at: datetime,
) -> list[DailySummaryStats]:
    """
    Возвращает статистику по активным нишам компании
    за интервал [started_at, ended_at).
    """

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                n.id AS niche_id,
                n.name AS niche_name,
                c.id AS company_id,
                c.name AS company_name,

                COUNT(lr.id) AS checked,

                COUNT(lr.id) FILTER (
                    WHERE lr.ai_lead = TRUE
                ) AS leads_found,

                COUNT(lr.id) FILTER (
                    WHERE lr.feedback IS NOT NULL
                ) AS rated,

                COUNT(lr.id) FILTER (
                    WHERE lr.feedback = 'good'
                ) AS good,

                COUNT(lr.id) FILTER (
                    WHERE lr.feedback = 'bad'
                ) AS bad,

                COUNT(lr.id) FILTER (
                    WHERE lr.feedback = 'skip'
                ) AS skipped,

                COUNT(lr.id) FILTER (
                    WHERE lr.feedback = 'spam'
                ) AS spam,

                ROUND(
                    AVG(lr.niche_score) FILTER (
                        WHERE lr.ai_lead = TRUE
                    ),
                    1
                ) AS avg_niche_score,

                ROUND(
                    AVG(lr.intent_score) FILTER (
                        WHERE lr.ai_lead = TRUE
                    ),
                    1
                ) AS avg_intent_score,

                COUNT(lr.id) FILTER (
                    WHERE lr.ai_lead = TRUE
                      AND m.reply_to_id IS NULL
                ) AS without_reply,

                COUNT(lr.id) FILTER (
                    WHERE lr.ai_lead = TRUE
                      AND m.reply_to_id IS NOT NULL
                      AND m.user_id IS NOT NULL
                      AND reply_message.user_id IS NOT NULL
                      AND m.user_id = reply_message.user_id
                ) AS reply_same_author,

                COUNT(lr.id) FILTER (
                    WHERE lr.ai_lead = TRUE
                      AND m.reply_to_id IS NOT NULL
                      AND m.user_id IS NOT NULL
                      AND reply_message.user_id IS NOT NULL
                      AND m.user_id <> reply_message.user_id
                ) AS reply_other_author,

                COUNT(lr.id) FILTER (
                    WHERE lr.ai_lead = TRUE
                      AND m.reply_to_id IS NOT NULL
                      AND (
                          m.user_id IS NULL
                          OR reply_message.user_id IS NULL
                      )
                ) AS reply_unknown_author,

                COUNT(lr.id) FILTER (
                    WHERE lr.feedback = 'bad'
                      AND lr.niche_score IS NOT NULL
                      AND lr.intent_score IS NOT NULL
                      AND LEAST(
                          lr.niche_score,
                          lr.intent_score
                      ) BETWEEN 75 AND 79
                ) AS bad_score_75_79,

                COUNT(lr.id) FILTER (
                    WHERE lr.feedback = 'bad'
                      AND lr.niche_score IS NOT NULL
                      AND lr.intent_score IS NOT NULL
                      AND LEAST(
                          lr.niche_score,
                          lr.intent_score
                      ) >= 80
                ) AS bad_score_80_plus

            FROM niches n

            JOIN companies c
                ON c.id = n.company_id

            LEFT JOIN lead_results lr
                ON lr.niche_id = n.id
               AND lr.detected_at >= %s
               AND lr.detected_at < %s

            LEFT JOIN messages m
                ON m.id = lr.message_id

            LEFT JOIN messages reply_message
                ON reply_message.id = m.reply_to_id

            WHERE n.company_id = %s
              AND n.is_active = TRUE
              AND c.is_active = TRUE

            GROUP BY
                n.id,
                n.name,
                c.id,
                c.name

            ORDER BY n.id
            """,
            (
                started_at,
                ended_at,
                company_id,
            ),
        ).fetchall()

    typed_rows = cast(list[DailySummaryRow], rows)
    result: list[DailySummaryStats] = []

    for row in typed_rows:
        checked = row["checked"] or 0
        leads_found = row["leads_found"] or 0
        good = row["good"] or 0
        bad = row["bad"] or 0

        result.append(
            {
                "niche_id": NicheId(row["niche_id"]),
                "niche_name": row["niche_name"],
                "company_id": CompanyId(row["company_id"]),
                "company_name": row["company_name"],
                "checked": checked,
                "leads_found": leads_found,
                "rated": row["rated"] or 0,
                "good": good,
                "bad": bad,
                "skipped": row["skipped"] or 0,
                "spam": row["spam"] or 0,
                "avg_niche_score": decimal_to_float(
                    row["avg_niche_score"]
                ),
                "avg_intent_score": decimal_to_float(
                    row["avg_intent_score"]
                ),
                "without_reply": row["without_reply"] or 0,
                "reply_same_author": row["reply_same_author"] or 0,
                "reply_other_author": row["reply_other_author"] or 0,
                "reply_unknown_author": row["reply_unknown_author"] or 0,
                "bad_score_75_79": row["bad_score_75_79"] or 0,
                "bad_score_80_plus": row["bad_score_80_plus"] or 0,
                "lead_percent": (
                    round(leads_found * 100 / checked, 1)
                    if checked
                    else 0.0
                ),
                "precision": (
                    round(good * 100 / (good + bad), 1)
                    if good + bad
                    else None
                ),
            }
        )

    return result


def decimal_to_float(value: Decimal | None) -> float | None:
    if value is None:
        return None

    return float(value)

def get_active_summary_targets() -> list[SummaryTarget]:
    """
    Возвращает активные Telegram-конфигурации,
    для которых задан чат отправки.
    """

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                tc.company_id,
                tc.chat_id,
                tc.metrics_topic_id,
                c.name AS company_name
            FROM telegram_configs tc

            JOIN companies c
                ON c.id = tc.company_id

            WHERE tc.is_active = TRUE
              AND c.is_active = TRUE
              AND tc.chat_id IS NOT NULL

            ORDER BY tc.company_id
            """
        ).fetchall()

    return [
        {
            "company_id": CompanyId(row["company_id"]),
            "chat_id": TgChatId(row["chat_id"]),
            "metrics_topic_id": row["metrics_topic_id"],
            "company_name": str(row["company_name"]),
        }
        for row in rows
    ]


def get_last_24_hours_period() -> tuple[datetime, datetime]:
    """
    Возвращает последние 24 часа.
    В БД интервал передаётся в UTC.
    """

    ended_at = datetime.now(timezone.utc)
    started_at = ended_at - timedelta(hours=24)

    return started_at, ended_at


def format_period(
    started_at: datetime,
    ended_at: datetime,
) -> str:
    started_moscow = started_at.astimezone(MOSCOW_TZ)
    ended_moscow = ended_at.astimezone(MOSCOW_TZ)

    return (
        f"{started_moscow:%d.%m.%Y %H:%M} — "
        f"{ended_moscow:%d.%m.%Y %H:%M} МСК"
    )
