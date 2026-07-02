import json
import re
import hashlib
import unicodedata
from app.settings import (
    BASE_DIR,
    CHAR_REPLACEMENTS_FILE,
)

INVISIBLE_CHARS_PATTERN = re.compile(
    r"[\u200b\u200c\u200d\u2060\ufeff\u00ad]"
)


async def build_tg_link(event):
    chat = await event.get_chat()
    message_id = event.message.id

    username = getattr(chat, "username", None)

    if username:
        return f"https://t.me/{username}/{message_id}"

    chat_id = str(event.chat_id)

    # приватные супергруппы / каналы
    if chat_id.startswith("-100"):
        internal_id = chat_id[4:]
        return f"https://t.me/c/{internal_id}/{message_id}"

    return "Нет публичной ссылки"


def has_link(text):
    return bool(
        re.search(
            r"(https?://|www\.|t\.me/|telegram\.me/|tg://|tg:resolve|telegram://|tdesktop://|@\w+|\w+\.(ru|com|net|org|io|рф)\b)",
            text,
            re.IGNORECASE
        )
    )


def load_char_replacements():
    if not CHAR_REPLACEMENTS_FILE.exists():
        return {}

    replacements = {}

    for line in CHAR_REPLACEMENTS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()

        if not line or line.startswith("#"):
            continue

        if "=" not in line:
            continue

        source, target = line.split("=", 1)
        source = source.strip()
        target = target.strip()

        if source:
            replacements[source] = target

    return replacements


def apply_char_replacements(text):
    CHAR_REPLACEMENTS = load_char_replacements()

    for source, target in CHAR_REPLACEMENTS.items():
        text = text.replace(source, target)

    return text


def get_hash(text):
    text = normalize(text)
    return hashlib.md5(text.encode()).hexdigest()


def normalize(text):
    text = unicodedata.normalize("NFKC", text)
    text = INVISIBLE_CHARS_PATTERN.sub("", text)
    text = apply_char_replacements(text)
    text = text.lower()
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def extract_json(text):
    decoder = json.JSONDecoder()

    text = text.strip()

    start = text.find("{")

    if start == -1:
        return None

    try:
        data, _ = decoder.raw_decode(text[start:])
        return data

    except Exception as e:
        print("❌ JSON extract error:", e)
        return None


def load_lines(filename):
    path = BASE_DIR / "config" / filename

    if not path.exists():
        return []

    return [
        line.strip()
        for line in path.read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    ]


def load_text(filename):
    path = BASE_DIR / "config" / filename

    if not path.exists():
        return ""

    return path.read_text(
        encoding="utf-8"
    ).strip()
