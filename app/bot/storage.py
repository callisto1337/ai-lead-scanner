import json

from app.settings import BLACKLIST_PATH, PENDING_LEADS_PATH


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


def save_pending_lead(lead_id, data):
    storage = load_pending_leads()
    storage[lead_id] = data

    PENDING_LEADS_PATH.write_text(
        json.dumps(
            storage,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
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
