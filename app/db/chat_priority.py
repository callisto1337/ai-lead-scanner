from app.db.connection import get_connection
from app.settings import (
    CHAT_PRIORITY_FLOOR_RATE,
    CHAT_PRIORITY_PRIOR_STRENGTH,
    CHAT_PRIORITY_WINDOW_DAYS,
)
from app.types import NicheId, TgChatId


def refresh_chat_niche_priority() -> None:
    """
    Пересчитывает sample_rate для каждой пары (ниша, чат) по данным
    lead_results за последние CHAT_PRIORITY_WINDOW_DAYS дней. Окно
    короткое и не накопительное специально: если реальность чата
    резко поменялась (наплыв нового трафика/темы), она должна попасть
    в приоритет за дни, а не недели-месяцы. Холодный старт для пары
    без истории — глобальная средняя доля "да"/"спорно" по этой нише
    (тоже без ручной разметки, просто агрегат по остальным чатам).
    """
    with get_connection() as conn:
        conn.execute(
            """
            WITH niche_global AS (
                SELECT
                    niche_id,
                    COUNT(*) FILTER (
                        WHERE niche_match IN ('да', 'спорно')
                    )::float / GREATEST(COUNT(*), 1) AS global_rate
                FROM lead_results
                WHERE niche_match IS NOT NULL
                  AND detected_at >= now() - (%(window_days)s * INTERVAL '1 day')
                GROUP BY niche_id
            ),
            chat_stats AS (
                SELECT
                    lr.niche_id,
                    m.tg_chat_id,
                    COUNT(*) FILTER (
                        WHERE lr.niche_match IN ('да', 'спорно')
                    ) AS successes,
                    COUNT(*) AS total
                FROM lead_results lr
                JOIN messages m
                    ON m.id = lr.message_id
                WHERE lr.niche_match IS NOT NULL
                  AND lr.detected_at >= now() - (%(window_days)s * INTERVAL '1 day')
                GROUP BY lr.niche_id, m.tg_chat_id
            )
            INSERT INTO chat_niche_priority (
                niche_id, tg_chat_id, sample_rate, samples, successes, updated_at
            )
            SELECT
                cs.niche_id,
                cs.tg_chat_id,
                GREATEST(
                    (cs.successes + ng.global_rate * %(prior_strength)s)
                        / (cs.total + %(prior_strength)s),
                    %(floor_rate)s
                ) AS sample_rate,
                cs.total,
                cs.successes,
                now()
            FROM chat_stats cs
            JOIN niche_global ng
                ON ng.niche_id = cs.niche_id
            ON CONFLICT (niche_id, tg_chat_id) DO UPDATE
            SET sample_rate = EXCLUDED.sample_rate,
                samples     = EXCLUDED.samples,
                successes   = EXCLUDED.successes,
                updated_at  = EXCLUDED.updated_at
            """,
            {
                "window_days": CHAT_PRIORITY_WINDOW_DAYS,
                "prior_strength": CHAT_PRIORITY_PRIOR_STRENGTH,
                "floor_rate": CHAT_PRIORITY_FLOOR_RATE,
            },
        )


def get_chat_niche_sample_rate(
    niche_id: NicheId,
    tg_chat_id: TgChatId,
) -> float:
    """
    Читает закэшированный sample_rate. Для пары, которую ещё не успел
    увидеть refresh (новый чат, новая ниша) — пол по умолчанию, чтобы
    сразу начать копить наблюдения, а не ждать первого прогона.
    """
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT sample_rate
            FROM chat_niche_priority
            WHERE niche_id = %s
              AND tg_chat_id = %s
            """,
            (niche_id, tg_chat_id),
        ).fetchone()

    if row is None:
        return CHAT_PRIORITY_FLOOR_RATE

    return float(row["sample_rate"])
