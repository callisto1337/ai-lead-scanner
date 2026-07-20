from typing import TypedDict, cast

from app.db.connection import get_connection
from app.embeddings import create_embedding, embedding_to_pgvector
from app.settings import MEMORY_MAX_DISTANCE
from app.types import NicheId


class SimilarMessage(TypedDict):
    text: str
    human_lead: bool
    feedback: str
    score: int | None
    description: str | None
    distance: float


def find_similar_messages(
    text: str,
    niche_id: NicheId,
    limit: int = 6,
) -> list[SimilarMessage]:
    embedding = embedding_to_pgvector(
        create_embedding(text)
    )

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                m.text,
                lr.human_lead,
                lr.feedback,
                lr.score,
                lr.description,
                e.embedding <=> %s::vector AS distance
            FROM message_embeddings e
            JOIN messages m
                ON m.id = e.message_id
            JOIN lead_results lr
                ON lr.message_id = m.id
            WHERE lr.niche_id = %s
              AND lr.feedback IN ('good', 'bad')
              AND lr.human_lead IS NOT NULL
              AND e.embedding <=> %s::vector < %s
            ORDER BY distance ASC
            LIMIT %s
            """,
            (
                embedding,
                niche_id,
                embedding,
                MEMORY_MAX_DISTANCE,
                limit * 2,
            ),
        ).fetchall()

    typed_rows = cast(list[SimilarMessage], rows)

    return balance_examples(
        typed_rows,
        limit,
    )


def balance_examples(
    rows: list[SimilarMessage],
    limit: int,
) -> list[SimilarMessage]:
    good: list[SimilarMessage] = []
    bad: list[SimilarMessage] = []

    for row in rows:
        if row["human_lead"] is True:
            good.append(row)
        else:
            bad.append(row)

    result: list[SimilarMessage] = []

    for good_row, bad_row in zip(good, bad):
        result.extend(
            (
                good_row,
                bad_row,
            )
        )

        if len(result) >= limit:
            return result[:limit]

    for row in rows:
        if row not in result:
            result.append(row)

        if len(result) >= limit:
            break

    return result