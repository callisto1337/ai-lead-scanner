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

    result["user_id"] = sender["id"]

    username = sender["username"]

    if username:
        escaped_username = html.escape(username)
        result["user_link"] = (
            f'<a href="https://t.me/{escaped_username}">'
            f"@{escaped_username}</a>"
        )
    else:
        result["user_link"] = f"ID: {sender['id']}"