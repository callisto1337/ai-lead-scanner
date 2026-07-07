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

CHAR_REPLACEMENTS_FILE = CONFIG_DIR / "char_replacements.txt"
POSTGRES_DB = os.getenv("POSTGRES_DB", "")
POSTGRES_USER = os.getenv("POSTGRES_USER", "")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@postgres:5432/{POSTGRES_DB}"
)

PROMETHEUS_URL = "http://prometheus:9090"

MODEL_API_URL = os.getenv("MODEL_API_URL", "http://lead-scanner-model-api:8000")
MODEL_NAME = os.getenv("MODEL_NAME", "qwen2.5:7b")
AI_TIMEOUT_SECONDS = int(os.getenv("AI_TIMEOUT_SECONDS", "90"))