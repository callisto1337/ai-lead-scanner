from app.db.connection import get_connection


def get_active_stopwords() -> list[str]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT phrase
            FROM global_stopwords
            WHERE is_active = TRUE
            ORDER BY id
            """
        ).fetchall()

    return [row["phrase"] for row in rows]