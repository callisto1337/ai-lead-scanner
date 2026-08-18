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


# Слово, смешивающее латиницу и кириллицу (например, "fвs" вместо "фбс"
# или "httрs" вместо "https") — обычный человек так не печатает,
# это осознанный обход текстовых фильтров похожими по начертанию буквами.
MIXED_SCRIPT_WORD_PATTERN = re.compile(
    r"\b(?=\w*[a-zA-Z])(?=\w*[а-яёА-ЯЁ])\w{3,}\b"
)


def has_mixed_script_word(text: str) -> bool:
    return bool(MIXED_SCRIPT_WORD_PATTERN.search(text))


def word_stem_pattern(word: str) -> str:
    # Русский язык склоняется — не требуем точного совпадения окончания.
    # Короткие слова (коды, аббревиатуры) оставляем точными, чтобы не
    # ловить случайные совпадения на 2-3 буквах.
    if len(word) <= 3:
        return re.escape(word)

    if len(word) <= 5:
        return re.escape(word[:-1]) + r"\w*"

    return re.escape(word[:-2]) + r"\w*"


def build_stopword_pattern(normalized_word: str) -> str | None:
    words = re.findall(r"\w+", normalized_word)

    if not words:
        return None

    stems = [word_stem_pattern(word) for word in words]

    # Разделитель между словами фразы — любые не-словесные символы
    # (пробел, точка, дефис и т.д.), не важно, как ввели в админке.
    return r"(?<!\w)" + r"\W+".join(stems)


def find_stopword(
    text: str,
    stopwords: Iterable[str],
) -> str | None:
    normalized_text = normalize(text)

    for word in stopwords:
        normalized_word = normalize(word)

        pattern = build_stopword_pattern(normalized_word)

        if pattern is None:
            continue

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

    if has_mixed_script_word(clean_text):
        return reject("mixed_script")

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