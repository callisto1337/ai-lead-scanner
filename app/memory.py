import json
from app.settings import BASE_DIR

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

    item_id = item.get("id")

    if item_id:
        memory = [
            existing
            for existing in memory
            if existing.get("id") != item_id
        ]

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


def delete_memory(item_id):
    if not item_id:
        return

    memory = [
        item
        for item in load_memory()
        if item.get("id") != item_id
    ]

    MEMORY_PATH.write_text(
        json.dumps(
            memory,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )
