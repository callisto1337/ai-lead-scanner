from app.db import exists_seen_message
from app.utils import normalize, load_lines, get_hash

STOPWORDS_LIST = load_lines("stopwords.txt")


def reject(reason) -> object:
    return {
        "ok": False,
        "reason": reason,
    }


def has_stopword(text: str):
    text_lower = normalize(text)

    for word in STOPWORDS_LIST:
        if normalize(word) in text_lower:
            return word

    return None


def is_duplicate(text: str) -> bool:
    normalized_text = normalize(text)
    msg_hash = get_hash(normalized_text)

    return exists_seen_message(msg_hash)


def prefilter_message(text: str) -> object:
    if not text:
        return reject("Пустое сообщение")

    clean_text = text.strip()

    if not clean_text:
        return reject("Пустое сообщение")

    # Сначала проверяем/сохраняем увиденное сообщение
    if is_duplicate(clean_text):
        return reject("Спам / дубль сообщения")

    if len(clean_text) > 1000:
        return reject("Сообщение слишком длинное")

    if len(clean_text) < 20:
        return reject("Сообщение слишком короткое")

    stopword = has_stopword(clean_text)

    if stopword:
        return reject(f"Сообщение отфильтровано стоп-словом: {stopword}")

    return {
        "ok": True,
        "reason": None,
    }
