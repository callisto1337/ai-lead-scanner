from telethon import TelegramClient, events
from telethon.errors import FloodWaitError
from prefilter import prefilter_message
from filter import is_lead
from bot import send_to_leads, LEADS_CHAT_ID
from dotenv import load_dotenv
from utils import build_tg_link
from lifecycle import run_monitor
from metrics import (
    message_received,
    spam_detected,
    lead_detected,
    ai_request,
    AI_TIME
)
from settings import SESSIONS_DIR, API_ID, API_HASH, BASE_DIR
import html
import sys
import time

load_dotenv()

client = TelegramClient(
    str(SESSIONS_DIR / "lead_monitor"),
    API_ID,
    API_HASH
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
            sender.id,
            flush=True
        )
        return

    text = event.message.text
    clean_text = text.strip()
    short_text = clean_text[:100] + "..." if len(clean_text) > 100 else clean_text

    if not clean_text:
        return

    print("💬 Новое сообщение:", short_text, flush=True)

    message_received()
    prefilter_result = prefilter_message(clean_text)

    if not prefilter_result["ok"]:
        spam_detected()

        print(f"❌ {prefilter_result['reason']}", flush=True)
        print("---------------", flush=True)
        return

    ai_request()

    with AI_TIME.time():
        result = is_lead(clean_text)


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
        print("🔥 Найден лид", flush=True)

        lead_detected()
        result["link"] = await build_tg_link(event)

        try:
            sent = await send_to_leads(
                result,
            )

            if not sent:
                print(
                    "⚠️ Лид найден, но не отправлен в чат лидов",
                    flush=True
                )

        except Exception as e:
            print(
                f"❌ Ошибка при отправке лида: {e}",
                flush=True
            )
    else:
        print("❌ Нерелевантное сообщение", flush=True)

    print("🤖 Объяснение:", result.get("description", "Нет объяснения"), flush=True)
    print("---------------", flush=True)


run_monitor(client)
