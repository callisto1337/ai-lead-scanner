from app.settings import BLACKLIST_PATH


def blacklist_path():
    return BLACKLIST_PATH


def load_blacklist() -> set[str]:
    path = BLACKLIST_PATH

    if not path.exists():
        return set()

    return {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
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

    path = blacklist_path()

    try:
        existing = {
            line.strip()
            for line in path.read_text(
                encoding="utf-8"
            ).splitlines()
            if line.strip()
        }

    except:
        existing = set()

    if value in existing:
        return

    existing.add(value)

    path.write_text(
        "\n".join(sorted(existing)) + "\n",
        encoding="utf-8"
    )
