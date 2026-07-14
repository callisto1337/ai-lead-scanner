import html


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


def truncate_text(text: str, max_len: int = 1000) -> str:
    if len(text) <= max_len:
        return text

    return text[:max_len].rstrip() + "\n…обрезано"


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


def build_lead_message(
    result,
    rating_block: str | None=None,
):
    source_link = result.get("source_link")
    source_title = result.get("source_title")
    source_block = build_source_block(source_link, source_title)
    reply_text = result.get("reply_text")
    reply_author_relation = result.get("reply_author_relation")
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
            f"{reply_text}\n"
        )

    message = f"""
🔥 НОВЫЙ ЛИД
{reply_block}
💬 Сообщение:
<pre>{html.escape(result.get("text", ""))}</pre>

🤖 AI:
{html.escape(str(result.get("description", "")))}

👤 Пользователь:
{result.get("user_link", "нет ссылки")}

🔗 Источник:
{source_block}
"""

    if rating_block:
        message += f"\n\n{rating_block}"

    return message