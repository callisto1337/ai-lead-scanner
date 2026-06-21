from utils import normalize, load_lines, is_duplicate, is_duplicate_but_not_previously_lead

STOPWORDS_LIST = load_lines("stopwords.txt")


def reject(reason):
    return {
        "ok": False,
        "reason": reason,
    }


def accept():
    return {
        "ok": True,
        "reason": None,
    }


def has_stopword(text):
    text_lower = normalize(text)

    for word in STOPWORDS_LIST:
        if normalize(word) in text_lower:
            return word

    return None


def prefilter_message(text):
    if not text:
        return reject("Пустое сообщение")

    clean_text = text.strip()

    if not clean_text:
        return reject("Пустое сообщение")

    # Сначала проверяем/сохраняем увиденное сообщение
    if is_duplicate(clean_text):
        # Если это дубликат — решаем, считать ли его спамом с учётом памяти о лидах
        if is_duplicate_but_not_previously_lead(clean_text):
            return reject("Спам / дубль сообщения")

    if len(clean_text) > 1000:
        return reject("Сообщение слишком длинное")

    if len(clean_text) < 20:
        return reject("Сообщение слишком короткое")

    stopword = has_stopword(clean_text)

    if stopword:
        return reject(f"Сообщение отфильтровано стоп-словом: {stopword}")

    return accept()