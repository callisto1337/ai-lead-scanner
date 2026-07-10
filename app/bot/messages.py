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


def build_lead_message(
    lead,
    rating_block: str | None=None,
    history: list[str]|None=None,
):
    history_block = ""

    # if history:
    #     history_block = "\n💬 Контекст:\n"
    #
    #     for item in history:
    #         history_block += (
    #             f"<blockquote>{html.escape(item)}</blockquote>\n"
    #         )

    message = f"""
🔥 НОВЫЙ ЛИД
{history_block}
💬 Сообщение:
<pre>{html.escape(lead.get("text", ""))}</pre>

👤 Пользователь:
{lead.get("user_link", "нет ссылки")}

🔗 Источник:
{html.escape(lead.get("link", "нет ссылки"))}
"""

    if rating_block:
        message += f"\n\n{rating_block}"

    return message