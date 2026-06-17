async def build_tg_link(event):

    chat = await event.get_chat()
    message_id = event.message.id

    username = getattr(chat, "username", None)

    if username:
        return f"https://t.me/{username}/{message_id}"

    chat_id = str(event.chat_id)

    # приватные супергруппы / каналы
    if chat_id.startswith("-100"):
        internal_id = chat_id[4:]
        return f"https://t.me/c/{internal_id}/{message_id}"

    return "Нет публичной ссылки"

