from pathlib import Path
from dotenv import load_dotenv
import os


BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
SESSIONS_DIR = BASE_DIR / "sessions"

SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = str(os.getenv("API_HASH"))
BOT_TOKEN = str(os.getenv("BOT_TOKEN"))
LEADS_CHAT_ID = int(os.getenv("LEADS_CHAT_ID"))
