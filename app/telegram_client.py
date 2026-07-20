from telethon import TelegramClient  # pyright: ignore[reportMissingTypeStubs]
from app.settings import API_ID, API_HASH, SESSIONS_DIR


def create_client() -> TelegramClient:
    return TelegramClient(
        str(SESSIONS_DIR / "lead_monitor"),
        API_ID,
        API_HASH
    )
