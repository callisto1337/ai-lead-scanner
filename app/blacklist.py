from settings import CONFIG_DIR


def load_blacklist() -> set[str]:
    path = CONFIG_DIR / "blacklist.txt"

    if not path.exists():
        return set()

    return {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


def is_blacklisted(user_id: int) -> bool:
    return str(user_id) in load_blacklist()