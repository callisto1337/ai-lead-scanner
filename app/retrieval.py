from app.embeddings import create_embedding, embedding_to_pgvector
from app.db import get_connection


def find_similar_messages(text, niche_id: int, limit=5):
    embedding = embedding_to_pgvector(create_embedding(text))

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                m.id,
                m.text,
                m.tg_message_id,
                m.tg_chat_id,
                m.reply_to_id,

                lr.id AS lead_result_id,
                lr.human_lead,
                lr.ai_lead,
                lr.feedback,
                lr.description,

                e.embedding <=> %s::vector AS distance

            FROM message_embeddings e

            JOIN messages m
                ON m.id = e.message_id

            JOIN lead_results lr
                ON lr.message_id = m.id

            WHERE lr.niche_id = %s
              AND lr.human_lead IS NOT NULL
              AND e.embedding <=> %s::vector < 0.7

            ORDER BY distance

            LIMIT %s
            """,
            (
                embedding,
                niche_id,
                embedding,
                limit,
            )
        ).fetchall()

    return rows