from app.db.dedup import exists_seen_message
from app.db.stopwords import get_active_stopwords
from app.types import PrefilterResult
from app.utils import normalize, get_hash


def reject(reason: str) -> PrefilterResult:
    return {
        "ok": False,
        "reason": reason,
    }


def has_stopword(text: str) -> str | None:
    text_lower = normalize(text)

    for word in get_active_stopwords():
        normalized_word = normalize(word)

        if normalized_word and normalized_word in text_lower:
            return word

    return None


def is_duplicate(text: str) -> bool:
    normalized_text = normalize(text)
    msg_hash = get_hash(normalized_text)

    return exists_seen_message(msg_hash)


def prefilter_message(
    text: str,
    has_reply: bool = False,
) -> PrefilterResult:
    clean_text = text.strip() if text else None

    if not clean_text:
        return reject("empty")

    if is_duplicate(clean_text):
        return reject("duplicate")

    if len(clean_text) > 1000:
        return reject("too_long")

    if len(clean_text) < 20 and not has_reply:
        return reject("too_short")

    stopword = has_stopword(clean_text)

    if stopword:
        return reject("stopword")

    return {
        "ok": True,
        "reason": None,
    }
