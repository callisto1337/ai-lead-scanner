from app.db.connection import get_connection


def get_active_niches():
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                n.id,
                n.name,
                n.slug,
                n.company_id,
                c.name AS company_name,
                nc.about,
                nc.extra_instructions
            FROM niches n
            JOIN companies c
                ON c.id = n.company_id
            LEFT JOIN niche_configs nc
                ON nc.niche_id = n.id
            WHERE n.is_active = TRUE
              AND c.is_active = TRUE
            ORDER BY c.id, n.id
            """
        ).fetchall()

        niches = []

        for row in rows:
            keywords = conn.execute(
                """
                SELECT phrase
                FROM niche_keywords
                WHERE niche_id = %s
                  AND is_active = TRUE
                ORDER BY id
                """,
                (row["id"],)
            ).fetchall()

            blacklist = conn.execute(
                """
                SELECT phrase
                FROM niche_blacklist
                WHERE niche_id = %s
                  AND is_active = TRUE
                ORDER BY id
                """,
                (row["id"],)
            ).fetchall()

            niches.append({
                **row,
                "keywords": [item["phrase"] for item in keywords],
                "blacklist": [item["phrase"] for item in blacklist],
            })

        return niches


def get_niches_for_select():
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT
                n.id,
                n.name,
                c.name AS company_name
            FROM niches n
            JOIN companies c ON c.id = n.company_id
            ORDER BY c.name, n.name
            """
        ).fetchall()


def add_niche_keywords_bulk(niche_id: int, phrases: list[str]) -> int:
    clean_phrases = sorted({
        phrase.strip()
        for phrase in phrases
        if phrase.strip()
    })

    if not clean_phrases:
        return 0

    with get_connection() as conn:
        added = 0

        for phrase in clean_phrases:
            result = conn.execute(
                """
                INSERT INTO niche_keywords (
                    niche_id,
                    phrase,
                    is_active
                )
                VALUES (%s, %s, TRUE)
                ON CONFLICT(niche_id, phrase)
                DO NOTHING
                """,
                (niche_id, phrase),
            )

            added += result.rowcount

        conn.commit()

    return added


def add_niche_blacklist_bulk(niche_id: int, phrases: list[str]) -> int:
    clean_phrases = sorted({
        phrase.strip()
        for phrase in phrases
        if phrase.strip()
    })

    if not clean_phrases:
        return 0

    with get_connection() as conn:
        added = 0

        for phrase in clean_phrases:
            result = conn.execute(
                """
                INSERT INTO niche_blacklist (
                    niche_id,
                    phrase,
                    is_active
                )
                VALUES (%s, %s, TRUE)
                ON CONFLICT(niche_id, phrase)
                DO NOTHING
                """,
                (niche_id, phrase),
            )

            added += result.rowcount

        conn.commit()

    return added