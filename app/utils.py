import json
import re
import hashlib
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

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


def get_hash(text):
    text = normalize(text)
    return hashlib.md5(text.encode()).hexdigest()


def is_duplicate(text):
    path = BASE_DIR / "config" / "seen_messages.json"

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except:
        data = []

    msg_hash = get_hash(text)

    now = datetime.now()

    for item in data:
        if item["hash"] == msg_hash:
            return True

    data.append({
        "hash": msg_hash,
        "time": str(now)
    })

    # храним последние 5000
    data = data[-5000:]

    path.write_text(
        json.dumps(data, ensure_ascii=False),
        encoding="utf-8"
    )

    return False


def normalize(text):
    return re.sub(r"\s+", " ", text.lower()).strip()


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
