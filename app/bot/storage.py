from app.db import save_message, save_embedding
from app.settings import BLACKLIST_PATH
from app.embeddings import create_embedding


def save_pending_message(message_id, data, save_vector: bool = True):
    save_message(
        message_id,
        data
    )

    if save_vector:
        embedding = create_embedding(data["text"])

        save_embedding(
            message_id,
            embedding
        )


def remove_from_blacklist(value):
    if not value:
        return

    value = str(value).strip()

    if not value:
        return

    try:
        existing = [
            line.strip()
            for line in BLACKLIST_PATH.read_text(
                encoding="utf-8"
            ).splitlines()
            if line.strip()
        ]

    except:
        return

    filtered = [
        item
        for item in existing
        if item != value
    ]

    if len(filtered) == len(existing):
        return

    BLACKLIST_PATH.write_text(
        "\n".join(filtered) + ("\n" if filtered else ""),
        encoding="utf-8"
    )
