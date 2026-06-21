import json
import re
import hashlib
import unicodedata
from difflib import SequenceMatcher
from settings import (
    BASE_DIR,
    CHAR_REPLACEMENTS_FILE,
    DUPLICATE_SIMILARITY_THRESHOLD,
    DUPLICATE_COMPARE_LIMIT,
    SEEN_MESSAGES_PATH
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
    path = BASE_DIR / "config" / CHAR_REPLACEMENTS_FILE

    if not path.exists():
        return {}

    replacements = {}

    for line in path.read_text(encoding="utf-8").splitlines():
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


def is_similar_text(first, second):
    if not first or not second:
        return False

    if min(len(first), len(second)) < 20:
        return False

    ratio = SequenceMatcher(
        None,
        first,
        second
    ).ratio()

    return ratio >= DUPLICATE_SIMILARITY_THRESHOLD


def ensure_seen_messages_storage():
    path = SEEN_MESSAGES_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    if not path.exists():
        path.write_text(
            "[]",
            encoding="utf-8"
        )


def is_duplicate_but_not_previously_lead(text) -> bool:
    """Возвращает True, если сообщение дубликат и ранее похожие сообщения НЕ были помечены как лид.

    Если же найден похожий в памяти элемент, помеченный как lead (lead == True),
    считаем, что это не спам и возвращаем False.
    """
    # убедимся, что файл для увиденных сообщений существует
    ensure_seen_messages_storage()

    # повторим логику определения дубля, но без записи и с проверкой памяти
    path = SEEN_MESSAGES_PATH

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        data = []

    normalized_text = normalize(text)
    msg_hash = get_hash(text)

    duplicate = False

    for item in data:
        if item.get("hash") == msg_hash:
            duplicate = True
            break

    if not duplicate:
        recent_items = data[-DUPLICATE_COMPARE_LIMIT:]

        for item in recent_items:
            previous_text = item.get("text", "")

            if is_similar_text(normalized_text, previous_text):
                duplicate = True
                break

    if not duplicate:
        return False

    # Если дубликат — проверить память о помеченных лидах
    try:
        from memory import load_memory

        memory = load_memory()
    except Exception:
        memory = []

    for mem in memory:
        mem_text = mem.get("text", "")
        if is_similar_text(normalized_text, normalize(mem_text)) and mem.get("lead"):
            # ранее похожее сообщение было признано лидом — не считать текущий спамом
            return False

    # дубликат и похожих лидов в памяти не найдено — считаем спамом
    return True


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
