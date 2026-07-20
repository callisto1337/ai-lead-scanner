from typing import cast

from app.db.connection import get_connection
from app.embeddings import Embedding
from app.types import MessageWithoutEmbedding, MessageId

EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"


def save_embedding(message_id: MessageId, embedding: Embedding) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO message_embeddings (
                message_id,
                embedding,
                model
            )
            VALUES (%s, %s, %s)
            ON CONFLICT(message_id, model)
            DO NOTHING
            """,
            (message_id, embedding, EMBEDDING_MODEL)
        )

        conn.commit()


def get_messages_without_embeddings(
    limit: int = 10,
) -> list[MessageWithoutEmbedding]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT m.*
            FROM messages m
            LEFT JOIN message_embeddings e
                ON e.message_id = m.id
            WHERE e.id IS NULL
            LIMIT %s
            """,
            (limit,),
        ).fetchall()

    return cast(list[MessageWithoutEmbedding], rows)