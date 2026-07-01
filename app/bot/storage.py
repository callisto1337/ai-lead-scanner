import json

from app.db import get_message, save_message, save_embedding
from app.settings import BLACKLIST_PATH, PENDING_LEADS_PATH
from app.embeddings import create_embedding


def ensure_pending_storage():
    PENDING_LEADS_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not PENDING_LEADS_PATH.exists():
        PENDING_LEADS_PATH.write_text(
            "{}",
            encoding="utf-8"
        )


def load_pending_leads():
    ensure_pending_storage()

    try:
        return json.loads(
            PENDING_LEADS_PATH.read_text(
                encoding="utf-8"
            )
        )

    except:
        return {}


def load_pending_lead(message_id):
    lead = get_message(message_id)

    if lead:
        return lead

    return load_pending_leads().get(message_id)


def save_pending_lead(message_id, data, save_vector: bool = True):
    storage = load_pending_leads()
    storage[message_id] = data

    PENDING_LEADS_PATH.write_text(
        json.dumps(
            storage,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

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
