import html
from typing import Any


def build_rater_info(user):
    if not user:
        return {
            "id": None,
            "username": None,
            "name": "",
            "text": "неизвестный аккаунт",
        }

    first_name = getattr(user, "first_name", None)
    last_name = getattr(user, "last_name", None)

    name_parts = [
        part
        for part in (first_name, last_name)
        if isinstance(part, str) and part
    ]

    full_name = " ".join(name_parts)

    username = getattr(user, "username", None)
    user_id = getattr(user, "id", None)

    if username:
        text = f"@{username}"
    elif full_name:
        text = f"{full_name} (ID: {user_id})"
    else:
        text = f"ID: {user_id}"

    return {
        "id": user_id,
        "username": username,
        "name": full_name,
        "text": text,
    }


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


def build_user_link(lead: dict[str, Any]) -> str:
    sender_name = str(lead.get("sender_name") or "").strip()
    sender_username = str(lead.get("sender_username") or "").lstrip("@").strip()
    sender_id = str(lead.get("sender_id") or "").strip()

    if sender_name:
        label = sender_name
    elif sender_username:
        label = f"@{sender_username}"
    else:
        label = sender_id

    if sender_username:
        url = f"https://t.me/{sender_username}"
    else:
        url = f"tg://user?id={sender_id}"

    return f'<a href="{html.escape(url, quote=True)}">{html.escape(label)}</a>'


def build_lead_message(
    result,
    rating_block: str | None=None,
):
    source_link = result.get("source_link")
    source_title = result.get("source_title")
    source_block = build_source_block(source_link, source_title)
    user_link = build_user_link(result)
    reply_text = result.get("reply_text")
    reply_author_relation = result.get("reply_author_relation")
    short_reply_text = truncate_text(reply_text, limit=200)
    reply_block = ""

    if reply_text:
        relation_label = {
            "тот же автор": "👤 Reply того же автора",
            "другой автор": "👥 Reply другого автора",
            "неизвестно": "❔ Автор reply неизвестен",
        }.get(
            reply_author_relation,
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
{html.escape(str(result.get("description", "")))}

👤 Пользователь:
{user_link}

🔗 Источник:
{source_block}
"""

    if rating_block:
        message += f"\n\n{rating_block}"

    return message