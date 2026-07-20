from typing import cast

import numpy as np
from numpy.typing import NDArray
from sentence_transformers import SentenceTransformer

from app.db.embeddings import save_embedding
from app.types import Embedding, MessageId


MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    global _model

    if _model is None:
        _model = SentenceTransformer(
            MODEL_NAME,
            cache_folder="/root/.cache/huggingface/sentence-transformers",
        )

    return _model


def create_embedding(text: str) -> Embedding:
    model = get_model()

    raw_result = model.encode(  # pyright: ignore[reportUnknownMemberType]
        text,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )

    result = cast(
        NDArray[np.float32],
        raw_result,
    )

    return result.astype(float).tolist()


def save_message_embedding(
    message_id: MessageId,
    text: str,
) -> None:
    embedding = create_embedding(text)
    save_embedding(message_id, embedding)


def embedding_to_pgvector(vector: Embedding) -> str:
    return str(vector)