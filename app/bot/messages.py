import html

from app.types import LeadResult


def truncate_text(
    text: str | None,
    limit: int = 200,
) -> str | None:
    if not text:
        return None

    text = text.strip()

    if len(text) <= limit:
        return text

    return text[:limit].rstrip() + "..."


def build_source_block(
    source_link: str | None,
    source_title: str | None,
) -> str:
    title = source_title or "Открыть источник"

    if not source_link:
        return f"{html.escape(title)}"

    return (
        f'<a href="{html.escape(source_link, quote=True)}">'
        f"{html.escape(title)}</a>"
    )


def build_user_link(lead: LeadResult) -> str:
    sender_name = str(lead.get("sender_name") or "").strip()
    sender_username = str(lead.get("sender_username") or "").lstrip("@").strip()
    sender_id = str(lead.get("sender_id") or "").strip()

    if sender_name:
        label = sender_name
    elif sender_username:
        label = f"@{sender_username}"
    elif sender_id:
        label = f"Пользователь {sender_id}"
    else:
        return "Не указан"

    if sender_username:
        url = f"https://t.me/{sender_username}"
    elif sender_id:
        url = f"tg://user?id={sender_id}"
    else:
        return html.escape(label)

    return (
        f'<a href="{html.escape(url, quote=True)}">'
        f"{html.escape(label)}"
        "</a>"
    )


REPLY_RELATION_LABELS: dict[str, str] = {
    "тот же автор": "👤 Reply того же автора",
    "другой автор": "👥 Reply другого автора",
    "неизвестно": "❔ Автор reply неизвестен",
}


def build_lead_message(
    result: LeadResult,
    rating_block: str | None = None,
) -> str:
    source_link = result.get("source_link")
    source_title = result.get("source_title")
    source_block = build_source_block(source_link, source_title)

    user_link = build_user_link(result)

    reply_text = result.get("reply_text")
    reply_author_relation = result.get("reply_author_relation")
    short_reply_text = truncate_text(reply_text, limit=200)

    reply_block = ""

    if reply_text:
        relation_label = REPLY_RELATION_LABELS.get(
            reply_author_relation or "",
            "↩️ Reply",
        )

        reply_block = (
            f"\n{relation_label}:\n"
            f"{short_reply_text}\n"
        )

    message = f"""
🔥 НОВЫЙ ЛИД
{reply_block}
💬 Сообщение:
<pre>{html.escape(result.get("text", ""))}</pre>

🤖 AI:
{html.escape(result.get("description", ""))}

👤 Пользователь:
{user_link}

🔗 Источник:
{source_block}
"""

    if rating_block:
        message += f"\n\n{rating_block}"

    return message