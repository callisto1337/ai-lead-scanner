from app.settings import BLACKLIST_PATH


def load_blacklist() -> set[str]:
    if not BLACKLIST_PATH.exists():
        return set()

    return {
        line.strip()
        for line in BLACKLIST_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


def is_blacklisted(user_id: int) -> bool:
    return str(user_id) in load_blacklist()


def add_to_blacklist(value):
    if not value:
        return

    value = str(value).strip()

    if not value:
        return

    try:
        existing = {
            line.strip()
            for line in BLACKLIST_PATH.read_text(
                encoding="utf-8"
            ).splitlines()
            if line.strip()
        }

    except:
        existing = set()

    if value in existing:
        return

    existing.add(value)

    BLACKLIST_PATH.write_text(
        "\n".join(sorted(existing)) + "\n",
        encoding="utf-8"
    )
