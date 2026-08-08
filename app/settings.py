from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()


def env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)

    if raw is None:
        return default

    value = raw.strip().lower()

    if value in ("1", "true", "yes", "on"):
        return True

    if value in ("0", "false", "no", "off"):
        return False

    raise ValueError(
        f"{name}: invalid boolean value '{raw}'"
    )


BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
SESSIONS_DIR = BASE_DIR / "sessions"

SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

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

PHOENIX_COLLECTOR_ENDPOINT = os.getenv(
    "PHOENIX_COLLECTOR_ENDPOINT",
    "http://phoenix:6006/v1/traces",
)
PHOENIX_PROJECT_NAME = os.getenv("PHOENIX_PROJECT_NAME", "lead-scanner")
PHOENIX_ENABLED = env_flag("PHOENIX_ENABLED", True)

MIN_NICHE_SCORE = int(os.getenv("MIN_NICHE_SCORE", "75"))
MIN_INTENT_SCORE = int(os.getenv("MIN_INTENT_SCORE", "75"))

MEMORY_MAX_DISTANCE = float(os.getenv("MEMORY_MAX_DISTANCE", "0.45"))

USER_LEAD_COOLDOWN_MINUTES = int(
    os.getenv("USER_LEAD_COOLDOWN_MINUTES", "60")
)

BOT_ADMIN_IDS = {
    int(value.strip())
    for value in os.getenv("BOT_ADMIN_IDS", "").split(",")
    if value.strip()
}

MESSAGE_WORKERS_COUNT = int(
    os.getenv("MESSAGE_WORKERS_COUNT", "4")
)
