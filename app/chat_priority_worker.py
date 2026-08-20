import asyncio
import traceback

from app.db.chat_priority import refresh_chat_niche_priority
from app.settings import CHAT_PRIORITY_REFRESH_SECONDS


async def chat_priority_worker() -> None:
    while True:
        try:
            await asyncio.to_thread(refresh_chat_niche_priority)
        except Exception:
            print("❌ Ошибка пересчёта chat_niche_priority:", flush=True)
            traceback.print_exc()

        await asyncio.sleep(CHAT_PRIORITY_REFRESH_SECONDS)
