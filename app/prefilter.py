from app.db import get_seen_message
from app.utils import normalize, load_lines, get_hash, is_similar_text

STOPWORDS_LIST = load_lines("stopwords.txt")


def reject(reason):
    return {
        "ok": False,
        "reason": reason,
    }


def has_stopword(text):
    text_lower = normalize(text)

    for word in STOPWORDS_LIST:
        if normalize(word) in text_lower:
            return word

    return None


def is_duplicate(text):
    normalized_text = normalize(text)
    msg_hash = get_hash(normalized_text)
    row = get_seen_message(msg_hash)

    # точное совпадение по хэшу
    for item in row:
        if item.get("hash") == msg_hash:
            return True

    # проверка на похожесть
    for item in row:
        if is_similar_text(
            normalized_text,
            item["normalized_text"]
        ):
            return True

    return False


def prefilter_message(text):
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
