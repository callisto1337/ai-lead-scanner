import hashlib
import re
import unicodedata

from app.settings import CHAR_REPLACEMENTS_FILE
from app.types import NewMessageEvent


INVISIBLE_CHARS_PATTERN = re.compile(
    r"[\u200b\u200c\u200d\u2060\ufeff\u00ad]"
)


async def build_tg_link(
    event: NewMessageEvent,
) -> str:
    chat = await event.get_chat()
    message_id = event.message.id

    username = chat.username

    if username:
        return f"https://t.me/{username}/{message_id}"

    chat_id = event.chat_id

    if chat_id is None:
        return "Нет публичной ссылки"

    chat_id_str = str(chat_id)

    # Приватные супергруппы / каналы
    if chat_id_str.startswith("-100"):
        internal_id = chat_id_str[4:]
        return f"https://t.me/c/{internal_id}/{message_id}"

    return "Нет публичной ссылки"


def load_char_replacements() -> dict[str, str]:
    if not CHAR_REPLACEMENTS_FILE.exists():
        return {}

    replacements: dict[str, str] = {}

    lines = CHAR_REPLACEMENTS_FILE.read_text(
        encoding="utf-8",
    ).splitlines()

    for raw_line in lines:
        line = raw_line.strip()

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


def apply_char_replacements(text: str) -> str:
    char_replacements = load_char_replacements()

    for source, target in char_replacements.items():
        text = text.replace(source, target)

    return text


def get_hash(text: str) -> str:
    normalized_text = normalize(text)

    return hashlib.md5(
        normalized_text.encode("utf-8")
    ).hexdigest()


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = INVISIBLE_CHARS_PATTERN.sub("", text)
    text = apply_char_replacements(text)
    text = text.lower()
    text = re.sub(r"\s+", " ", text)

    return text.strip()