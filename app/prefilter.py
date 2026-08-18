import re
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


# "p"/"e" учитывают частую обфускацию ссылок похожими кириллическими
# буквами (р, е) — см. config/char_replacements.txt.
BARE_LINK_PATTERN = re.compile(
    r"(?:https?|httр)s?://\S+|t\.m[eе]/\S+|www\.\S+",
    re.IGNORECASE,
)


def is_bare_link(text: str) -> bool:
    stripped = BARE_LINK_PATTERN.sub("", text)
    stripped = re.sub(r"[\s\W_]+", "", stripped)

    return not stripped


def find_stopword(
    text: str,
    stopwords: Iterable[str],
) -> str | None:
    normalized_text = normalize(text)

    for word in stopwords:
        normalized_word = normalize(word)

        pattern = r"(?<!\w)" + re.escape(normalized_word) + r"(?!\w)"

        if re.search(pattern, normalized_text):
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

    if is_bare_link(clean_text):
        return reject("bare_link")

    stopword = has_stopword(clean_text)

    if stopword:
        return reject(
            "global_stopword"
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