from app.embeddings import create_embedding, embedding_to_pgvector
from app.db import get_connection


def find_similar_messages(text, limit=5):
    embedding = embedding_to_pgvector(create_embedding(text))

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT 
                m.text,
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
