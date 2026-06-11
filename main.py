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

@client.on(events.NewMessage())
async def handler(event):

    # if event.out:
    #     return

    # игнорируем сообщения Telegram-бота
    sender = await event.get_sender()

    if sender and getattr(sender, "bot", False):
        return

    text = event.message.text

    if not text:
        return


    result = is_lead(text)


    if not result:
        return


    if result["relevant"] == 1 and result["score"] >= 50:

        print("🔥 Найден лид")

        await send_to_leads(
            result
        )


print("Запуск...")

client.start()

print("Клиент запущен")

client.run_until_disconnected()