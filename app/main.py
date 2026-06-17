from telethon import TelegramClient, events
from telethon.errors import FloodWaitError
from utils import has_link, is_duplicate
from filter import is_lead
from bot import send_to_leads, LEADS_CHAT_ID
from dotenv import load_dotenv
from pathlib import Path
from utils import build_tg_link
import os
import html
import sys
import time

BASE_DIR = Path(__file__).resolve().parent.parent
SESSIONS_DIR = BASE_DIR / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


load_dotenv()


api_id = int(os.getenv("API_ID"))
api_hash = str(os.getenv("API_HASH"))


client = TelegramClient(
    str(SESSIONS_DIR / "lead_monitor"),
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

    if is_duplicate(text):
        print("❌ Спам")
        print("---------------", flush=True)
        return

    if len(clean_text) > 1000:
        print(
            "❌ Сообщение слишком длинное",
        )
        print("---------------", flush=True)
        return

    if len(clean_text) < 20:
        print(
            "❌ Сообщение слишком короткое",
        )
        print("---------------", flush=True)
        return

    if has_link(text):
        print(
            "❌ В сообщении есть ссылки",
        )
        print("---------------", flush=True)
        return

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


print("🚀 Запуск мониторинга...", flush=True)
sys.stdout.flush()

try:
    client.start()
    print("🖥️ Мониторинг запущен", flush=True)
    sys.stdout.flush()
    client.run_until_disconnected()

except FloodWaitError as e:
    wait_seconds = int(getattr(e, "seconds", 3600))
    wait_hours = round(wait_seconds / 3600, 2)

    print(
        f"⏳ Telegram ограничил повторные попытки. FloodWait: {wait_seconds} секунд "
        f"≈ {wait_hours} часов.",
        flush=True
    )
    print(
        "🛑 Контейнер будет остановлен без немедленного перезапуска.",
        flush=True
    )

    sys.stderr.flush()
    time.sleep(min(wait_seconds, 3600))
    sys.exit(1)

except KeyboardInterrupt:
    print("🛑 Остановка мониторинга пользователем", flush=True)
    sys.exit(0)

except Exception as e:
    print(f"❌ Ошибка: {e}", flush=True)
    sys.stderr.flush()

    import traceback
    traceback.print_exc()

    print(
        "⏸️ Пауза 10 минут перед завершением, чтобы Docker не устроил быстрый цикл перезапусков.",
        flush=True
    )
    time.sleep(600)

    sys.exit(1)
