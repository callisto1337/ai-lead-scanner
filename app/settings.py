from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()


BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
SESSIONS_DIR = BASE_DIR / "sessions"

SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = str(os.getenv("API_HASH", ""))
BOT_TOKEN = str(os.getenv("BOT_TOKEN", ""))
CHAT_ID = int(os.getenv("CHAT_ID", "0"))
METRICS_TOPIC_ID = int(os.getenv("METRICS_TOPIC_ID", "0"))
LEADS_TOPIC_ID = int(os.getenv("LEADS_TOPIC_ID", "0"))
PROMETHEUS_URL = "http://prometheus:9090"

CHAR_REPLACEMENTS_FILE = CONFIG_DIR / "char_replacements.txt"
BLACKLIST_PATH = CONFIG_DIR / "blacklist.txt"
PENDING_LEADS_PATH = CONFIG_DIR / "pending_leads.json"
SEEN_MESSAGES_PATH = CONFIG_DIR / "seen_messages.json"

DUPLICATE_SIMILARITY_THRESHOLD = float(
    os.getenv("DUPLICATE_SIMILARITY_THRESHOLD", "0.9")
)
DUPLICATE_COMPARE_LIMIT = int(
    os.getenv("DUPLICATE_COMPARE_LIMIT", "500")
)

