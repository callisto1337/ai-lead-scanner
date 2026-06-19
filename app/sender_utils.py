def enrich_sender_info(result: dict, sender) -> None:
    if sender:
        result["user_id"] = sender.id

        if sender.username:
            username = html.escape(sender.username)
            result["user_link"] = f'<a href="https://t.me/{username}">@{username}</a>'
        else:
            result["user_link"] = f"ID: {sender.id}"
    else:
        result["user_id"] = None
        result["user_link"] = "нет ссылки"