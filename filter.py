import json
import ollama
from pathlib import Path
import re

BASE_DIR = Path(__file__).parent


# ---------------- MEMORY ----------------

def load_memory():
    path = BASE_DIR / "config" / "memory.json"

    if not path.exists():
        return []

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except:
        return []


def save_memory(item):
    path = BASE_DIR / "config" / "memory.json"

    memory = load_memory()

    memory.append(item)

    memory = memory[-200:]

    path.write_text(
        json.dumps(memory, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


# ---------------- CONFIG ----------------

def load_lines(filename):
    path = BASE_DIR / "config" / filename

    if not path.exists():
        return []

    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def load_text(filename):
    path = BASE_DIR / "config" / filename

    if not path.exists():
        return ""

    return path.read_text(encoding="utf-8").strip()


KEYWORDS = load_lines("keywords.txt")
BLACKLIST = load_lines("blacklist.txt")
ABOUT = load_text("about.txt")


# ---------------- CORE ----------------

def is_lead(text):
    if not text:
        return None

    text_lower = text.lower()
    memory = load_memory()

    # -------- blacklist fast path --------
    for word in BLACKLIST:
        if word.lower() in text_lower:
            print("⛔ BLACKLIST:", word)
            return {
                "relevant": 0,
                "score": 0,
                "category": "blacklist",
                "reason": f"blocked by {word}",
                "text": text
            }

    # -------- examples from memory --------
    examples = ""
    for m in memory[-30:]:
        examples += f"""
Сообщение:
{m.get('text')}
Оценка:
relevant={m.get('relevant')}, score={m.get('score')}
---
"""

    # -------- prompt --------
    prompt = f"""
Ты API-модель.

Твой задача фильтровать и искать потенциальных лидов для компании, информация о которой указана ниже.
Твой ответ будет обработан программой.

КРИТИЧЕСКИЕ ПРАВИЛА:
1. Ответ только один JSON объект
2. Никакого текста до JSON
3. Никакого текста после JSON
4. Не пиши несколько вариантов
5. После символа }} остановись

ОТВЕЧАЙ СТРОГО JSON БЕЗ ТЕКСТА (пример ниже).

ФОРМАТ:
{{
  "relevant": 0 или 1,
  "score": 0-100,
  "category": "регистрация, маркировка, обучение, интеграция, другое",
  "reason": "коротко укажи тут объяснение, почему дал такую оченку"
}}

КОМПАНИЯ:
{ABOUT}

КЛЮЧЕВЫЕ ТЕМЫ:
{chr(10).join(KEYWORDS)}

ОПЫТ:
{examples}

ВАЖНО:
- не пиши объяснений (только короткую причину в поле reason)
- не добавляй текст кроме JSON

СООБЩЕНИЕ:
{text}
"""

    try:
        response = ollama.chat(
            model="llama3.2",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        content = response["message"]["content"].strip()

        print("RAW:", content)

        # -------- extract JSON safely --------
        data = extract_json(content)

        if not data:
            return None

        result = {
            "relevant": int(data.get("relevant", 0)),
            "score": int(data.get("score", 0)),
            "category": data.get("category", "другое"),
            "reason": data.get("reason", ""),
            "text": text
        }

        return result

    except Exception as e:
        print("❌ Ollama error:", e)

        return None


def extract_json(text):
    decoder = json.JSONDecoder()

    text = text.strip()

    # ищем первую открывающую скобку
    start = text.find("{")

    if start == -1:
        return None

    try:
        data, end = decoder.raw_decode(text[start:])
        return data

    except Exception as e:
        print("❌ JSON extract error:", e)
        return None