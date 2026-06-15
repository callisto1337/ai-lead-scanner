from telethon import TelegramClient, events
from filter import is_lead
from bot import send_to_leads, LEADS_CHAT_ID
from dotenv import load_dotenv
import os


load_dotenv()


api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")


client = TelegramClient(
    "lead_monitor",
    api_id,
    api_hash
)


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



@client.on(events.NewMessage())
async def handler(event):

    # if event.out:
    #     return
    #
    # if event.chat_id == LEADS_CHAT_ID:
    #     return

    sender = await event.get_sender()

    if sender and getattr(sender, "bot", False):
        return

    text = event.message.text

    if not text:
        return


    result = is_lead(text)


    if not result:
        return


    if sender:

        if sender.username:
            user_link = f"https://t.me/{sender.username}"

        else:
            user_link = f"tg://user?id={sender.id}"

    else:
        user_link = "нет ссылки"


    result["user_link"] = user_link

    if result["lead"]:
        print("🔥 Найден лид")

        result["link"] = await build_tg_link(event)

        await send_to_leads(
            result,
        )
    else:
        print(
            "💬 Нерелевантное сообщение:",
            text
        )


print("🚀 Запуск...")


client.start()


print("✅ Клиент запущен")


client.run_until_disconnected()