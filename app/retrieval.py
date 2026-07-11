from app.embeddings import create_embedding, embedding_to_pgvector
from app.db import get_connection
from app.settings import MEMORY_MAX_DISTANCE


def find_similar_messages(text: str, niche_id: int, limit: int = 6):
    embedding = embedding_to_pgvector(create_embedding(text))

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

    return balance_examples(rows, limit)


def balance_examples(rows, limit: int):
    good = []
    bad = []

    for row in rows:
        if row["human_lead"] is True:
            good.append(row)
        elif row["human_lead"] is False:
            bad.append(row)

    result = []

    for pair in zip(good, bad):
        result.extend(pair)

        if len(result) >= limit:
            return result[:limit]

    for row in rows:
        if row not in result:
            result.append(row)

        if len(result) >= limit:
            break

    return result