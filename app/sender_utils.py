import html

from app.types import TgUser, ProcessMessageResult


def enrich_sender_info(
    result: ProcessMessageResult,
    sender: TgUser | None,
) -> None:
    if sender is None:
        result["user_id"] = None
        result["user_link"] = "Нет ссылки"
        return

    user_id = sender["id"]
    username = sender["username"]

    display_name = " ".join(
        part
        for part in (
            sender["first_name"],
            sender["last_name"],
        )
        if part
    ).strip()

    result["user_id"] = user_id

    if username:
        link_text = display_name or f"@{username}"

        result["user_link"] = (
            f'<a href="https://t.me/{html.escape(username, quote=True)}">'
            f"{html.escape(link_text)}"
            "</a>"
        )
        return

    if display_name:
        result["user_link"] = (
            f'<a href="tg://user?id={user_id}">'
            f"{html.escape(display_name)}"
            "</a>"
        )
        return

    result["user_link"] = (
        f'<a href="tg://user?id={user_id}">'
        f"ID: {user_id}"
        "</a>"
    )