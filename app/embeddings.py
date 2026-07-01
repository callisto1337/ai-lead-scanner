from sentence_transformers import SentenceTransformer

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
