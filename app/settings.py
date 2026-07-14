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

CHAR_REPLACEMENTS_FILE = CONFIG_DIR / "char_replacements.txt"

POSTGRES_DB = os.getenv("POSTGRES_DB", "")
POSTGRES_USER = os.getenv("POSTGRES_USER", "")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@postgres:5432/{POSTGRES_DB}"
)

MODEL_API_URL = os.getenv("MODEL_API_URL", "http://lead-scanner-model-api:8000")
MODEL_NAME = os.getenv("MODEL_NAME", "qwen3:14b")
AI_TIMEOUT_SECONDS = int(os.getenv("AI_TIMEOUT_SECONDS", "90"))

MIN_NICHE_SCORE = int(os.getenv("MIN_NICHE_SCORE", "75"))
MIN_INTENT_SCORE = int(os.getenv("MIN_INTENT_SCORE", "75"))

MEMORY_MAX_DISTANCE = float(os.getenv("MEMORY_MAX_DISTANCE", "0.65"))

USER_LEAD_COOLDOWN_MINUTES = int(
    os.getenv("USER_LEAD_COOLDOWN_MINUTES", "60")
)