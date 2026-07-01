from sentence_transformers import SentenceTransformer
from app.db import save_embedding

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

_model = None


def get_model():
    global _model

    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)

    return _model


def create_embedding(text: str):
    model = get_model()

    result = model.encode(
        text,
        normalize_embeddings=True
    )

    return result.tolist()


def save_message_embedding(message_id: str, text: str):
    embedding = create_embedding(text)

    save_embedding(message_id, embedding)

def embedding_to_pgvector(vector):
    return str(vector)