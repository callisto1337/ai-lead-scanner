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

VLLM_URL = os.getenv("VLLM_URL", "http://lead-scanner-vllm:8000/v1")
VLLM_API_KEY = os.getenv("VLLM_API_KEY", "")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen3-14B-AWQ")
AI_TIMEOUT_SECONDS = int(os.getenv("AI_TIMEOUT_SECONDS", "90"))

# Гибридная схема: extraction и niche-match остаются на локальной модели
# (VLLM_URL/MODEL_NAME выше, бесплатно), а intent — на более сильной
# модели, где заметнее выигрыш в качестве. "local" — вся классификация
# на VLLM_URL как раньше; "yandex" — intent уходит на Yandex AI Studio.
INTENT_BACKEND = os.getenv("INTENT_BACKEND", "local")
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY", "")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID", "")
YANDEX_INTENT_MODEL = os.getenv("YANDEX_INTENT_MODEL", "aliceai-llm")
YANDEX_INTENT_TIMEOUT_SECONDS = int(
    os.getenv("YANDEX_INTENT_TIMEOUT_SECONDS", "60")
)

PHOENIX_COLLECTOR_ENDPOINT = os.getenv(
    "PHOENIX_COLLECTOR_ENDPOINT",
    "http://phoenix:6006/v1/traces",
)
PHOENIX_PROJECT_NAME = os.getenv("PHOENIX_PROJECT_NAME", "lead-scanner")
PHOENIX_ENABLED = env_flag("PHOENIX_ENABLED", True)

MEMORY_MAX_DISTANCE = float(os.getenv("MEMORY_MAX_DISTANCE", "0.45"))
NICHE_EXAMPLES_ENABLED = env_flag("NICHE_EXAMPLES_ENABLED", False)

# Если включено: niche_match/intent_match, отличные от "нет" в быстром
# проходе (без thinking), переспрашиваются повторно с thinking для
# уточнения. "нет" не переспрашивается — экономит основную часть трафика.
THINKING_RETRY_ENABLED = env_flag("THINKING_RETRY_ENABLED", False)
THINKING_MAX_TOKENS = int(os.getenv("THINKING_MAX_TOKENS", "2048"))
THINKING_TIMEOUT_SECONDS = int(os.getenv("THINKING_TIMEOUT_SECONDS", "180"))

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

MONITOR_STALE_THRESHOLD_SECONDS = int(
    os.getenv("MONITOR_STALE_THRESHOLD_SECONDS", "1800")
)
MONITOR_WATCHDOG_INTERVAL_SECONDS = int(
    os.getenv("MONITOR_WATCHDOG_INTERVAL_SECONDS", "60")
)
