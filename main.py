from telethon import TelegramClient, events
from filter import is_lead
from bot import send_to_leads, LEADS_CHAT_ID
from dotenv import load_dotenv
from pathlib import Path
import os
import html

BASE_DIR = Path(__file__).parent


load_dotenv()


api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")


client = TelegramClient(
    "sessions/lead_monitor",
    api_id,
    api_hash
)


def load_blacklist():
    path = BASE_DIR / "config" / "blacklist.txt"

    if not path.exists():
        return set()

    return {
        line.strip()
        for line in path.read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    }

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

    if event.out:
        return

    if event.chat_id == LEADS_CHAT_ID:
        return

    sender = await event.get_sender()

    if sender and getattr(sender, "bot", False):
        return

    if sender and str(sender.id) in load_blacklist():
        print(
            "⛔ BLACKLIST USER:",
            sender.id
        )
        return

    text = event.message.text

    if not text:
        return


    result = is_lead(text)


    if not result:
        return


    if sender:

        result["user_id"] = sender.id

        if sender.username:
            user_link = f'<a href="https://t.me/{html.escape(sender.username)}">@{html.escape(sender.username)}</a>'
        else:
            user_link = f"ID: {sender.id}"

    else:
        result["user_id"] = None
        user_link = "нет ссылки"


    result["user_link"] = user_link

    if result["lead"]:
        print("🔥 Найден лид")
        print("💬 Сообщение:", text)

        result["link"] = await build_tg_link(event)

        await send_to_leads(
            result,
        )
    else:
        print("💬 Нерелевантное сообщение:", text)

    print("🤖 Объяснение:", result.get("description", "Нет объяснения"))
    print("---------------")


print("🚀 Запуск...")


client.start()


print("✅ Клиент запущен")


client.run_until_disconnected()