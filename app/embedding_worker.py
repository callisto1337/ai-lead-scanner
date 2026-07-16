import asyncio

from app.db.embeddings import get_messages_without_embeddings
from app.embeddings import create_embedding, save_embedding


async def embedding_worker():
    while True:
        messages = get_messages_without_embeddings()

        for message in messages:
            embedding = create_embedding(
                message["text"]
            )

            save_embedding(
                message["id"],
                embedding
            )

        await asyncio.sleep(10)
