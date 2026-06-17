from pathlib import Path
import json

BASE_DIR = Path(__file__).parent.parent
MEMORY_PATH = BASE_DIR / "config" / "memory.json"

def memory_path():
    return

def load_memory():
    if not MEMORY_PATH.exists():
        return []
    try:
        return json.loads(
            MEMORY_PATH.read_text(encoding="utf-8")
        )
    except:
        return []

def save_memory(item):
    memory = load_memory()
    memory.append(item)
    memory = memory[-100:]

    MEMORY_PATH.write_text(
        json.dumps(
            memory,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )