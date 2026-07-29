from collections.abc import Iterable

from app.db.dedup import exists_seen_message
from app.db.stopwords import get_active_stopwords
from app.types import PrefilterResult
from app.utils import normalize, get_hash


def reject(reason: str) -> PrefilterResult:
    return {
        "ok": False,
        "reason": reason,
    }


def accept() -> PrefilterResult:
    return {
        "ok": True,
        "reason": None,
    }


def find_stopword(
    text: str,
    stopwords: Iterable[str],
) -> str | None:
    normalized_text = normalize(text)

    for word in stopwords:
        normalized_word = normalize(word)

        if (
            normalized_word
            and normalized_word in normalized_text
        ):
            return word

    return None


def has_stopword(text: str) -> str | None:
    return find_stopword(
        text=text,
        stopwords=get_active_stopwords(),
    )


def is_duplicate(text: str) -> bool:
    normalized_text = normalize(text)
    msg_hash = get_hash(normalized_text)

    return exists_seen_message(msg_hash)


def prefilter_message(
    text: str
) -> PrefilterResult:
    clean_text = text.strip() if text else None

    if not clean_text:
        return reject("empty")

    if is_duplicate(clean_text):
        return reject("duplicate")

    if len(clean_text) > 1000:
        return reject("too_long")

    if len(clean_text) < 30:
        return reject("too_short")

    stopword = has_stopword(clean_text)

    if stopword:
        return reject(
            f"global_stopword:{stopword}"
        )

    return accept()


def prefilter_niche_message(
    text: str,
    niche_stopwords: Iterable[str],
    reply_text: str | None = None,
) -> PrefilterResult:
    stopwords = tuple(niche_stopwords)

    current_stopword = find_stopword(
        text=text,
        stopwords=stopwords,
    )

    if current_stopword:
        return reject(
            f"niche_stopword:{current_stopword}"
        )

    if reply_text:
        reply_stopword = find_stopword(
            text=reply_text,
            stopwords=stopwords,
        )

        if reply_stopword:
            return reject(
                f"niche_reply_stopword:{reply_stopword}"
            )

    return accept()