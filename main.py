from telethon import TelegramClient, events
from filter import is_lead
from bot import send_to_leads
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

def build_tg_link(chat_id, message_id):
    # приватные супергруппы / каналы
    if str(chat_id).startswith("-100"):
        chat_id = str(chat_id)[4:]
        return f"https://t.me/c/{chat_id}/{message_id}"

    # публичные чаты
    return f"https://t.me/{chat_id}/{message_id}"

@client.on(events.NewMessage())
async def handler(event):

    # if event.out:
    #     return

    chat = await event.get_chat()

    chat_id = str(event.chat_id)
    message_id = event.message.id

    # игнорируем сообщения Telegram-бота
    sender = await event.get_sender()

    if sender and getattr(sender, "bot", False):
        return

    text = event.message.text

    if not text:
        return

    print("📩 Новое сообщение:", text)

    result = is_lead(text)

    if not result:
        print("⚠️ Сообщение не обработано фильтром:", text)
        return

    print("🧠 Результат фильтра:", result)

    if result["lead"] == 1 and result["score"] >= 50:

        print("🔥 Найден лид")
        result["link"] = build_tg_link(event.chat_id, event.message.id)

        await send_to_leads(
            result
        )
    else:
        print("💬 Нерелевантный запрос: " + text)


print("Запуск...")

client.start()

print("Клиент запущен")

client.run_until_disconnected()