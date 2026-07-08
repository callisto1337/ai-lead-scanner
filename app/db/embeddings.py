from app.db.connection import get_connection


EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"


def save_embedding(message_id: str, embedding):
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


def get_messages_without_embeddings(limit: int = 10):
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT m.*
            FROM messages m
            LEFT JOIN message_embeddings e
                ON e.message_id = m.id
            WHERE e.id IS NULL
            LIMIT %s
            """,
            (limit,)
        ).fetchall()