from app.embeddings import create_embedding
from app.db import get_connection


def find_similar_messages(text, limit=5):
    embedding = str(create_embedding(text))

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT m.id,
                   m.text,
                   m.ai_lead,
                   m.human_lead,
                   m.feedback,

                   e.embedding <=> %s::vector AS distance

            FROM message_embeddings e

                     JOIN messages m
                          ON m.id = e.message_id
            WHERE m.human_lead IS NOT NULL

            ORDER BY distance

            LIMIT %s
            """,
            (
                embedding,
                limit
            )
        ).fetchall()

    return rows
