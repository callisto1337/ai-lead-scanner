from typing import cast

from app.db.connection import get_connection
from app.types import NicheWithConfig, PhraseRow, NicheConfigRow


def get_active_niches_with_config() -> list[NicheWithConfig]:
    with get_connection() as conn:
        raw_rows = conn.execute(
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

        rows = cast(list[NicheConfigRow], raw_rows)
        niches: list[NicheWithConfig] = []

        for row in rows:
            raw_keywords = conn.execute(
                """
                SELECT phrase
                FROM niche_keywords
                WHERE niche_id = %s
                  AND is_active = TRUE
                ORDER BY id
                """,
                (row["id"],),
            ).fetchall()

            raw_blacklist = conn.execute(
                """
                SELECT phrase
                FROM niche_blacklist
                WHERE niche_id = %s
                  AND is_active = TRUE
                ORDER BY id
                """,
                (row["id"],),
            ).fetchall()

            keywords = cast(list[PhraseRow], raw_keywords)
            blacklist = cast(list[PhraseRow], raw_blacklist)

            niche: NicheWithConfig = {
                "id": row["id"],
                "name": row["name"],
                "slug": row["slug"],
                "company_id": row["company_id"],
                "company_name": row["company_name"],
                "about": row["about"],
                "extra_instructions": row["extra_instructions"],
                "keywords": [item["phrase"] for item in keywords],
                "blacklist": [item["phrase"] for item in blacklist],
            }

            niches.append(niche)

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