import json
import ollama
from pathlib import Path
import re
from memory import load_memory


BASE_DIR = Path(__file__).parent.parent


# ---------------- HELPERS ----------------

def normalize(text):
    return re.sub(r"\s+", " ", text.lower()).strip()


def extract_json(text):
    decoder = json.JSONDecoder()

    text = text.strip()

    start = text.find("{")

    if start == -1:
        return None

    try:
        data, _ = decoder.raw_decode(text[start:])
        return data

    except Exception as e:
        print("❌ JSON extract error:", e)
        return None


# ---------------- CONFIG ----------------

# ---------------- FILTER ----------------

def load_lines(filename):
    path = BASE_DIR / "config" / filename

    if not path.exists():
        return []

    return [
        line.strip()
        for line in path.read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    ]


def load_text(filename):
    path = BASE_DIR / "config" / filename

    if not path.exists():
        return ""

    return path.read_text(
        encoding="utf-8"
    ).strip()


KEYWORDS = load_lines("keywords.txt")
STOPWORDS_LIST = load_lines("stopwords.txt")
ABOUT = load_text("about.txt")


def format_config_list(items, fallback="Не указано"):
    if not items:
        return fallback

    return "\n".join(
        f"- {item}"
        for item in items
    )


def build_memory_examples(limit=30):
    memory = load_memory()

    if not memory:
        return "Пока нет примеров обратной связи."

    examples = []

    for item in memory[-limit:]:
        lead_value = "true" if item.get("lead") else "false"

        examples.append(
            f"""
Сообщение:
{item.get("text", "")}

Правильная оценка:
lead={lead_value}
feedback={item.get("feedback", "unknown")}
"""
        )

    return "\n---\n".join(examples)


def is_lead(text):

    if not text:
        return None


    text_lower = normalize(text)

    # быстрый стоп

    for word in STOPWORDS_LIST:
        if normalize(word) in text_lower:
            return {
                "lead": False,
                "text": text,
                "description": f"🚫 Сообщение отфильтровано стоп-словом: {word}"
            }


    memory_examples = build_memory_examples()

    keywords_text = format_config_list(
        KEYWORDS,
        "Ключевые фразы не указаны."
    )

    prompt = f"""
Ты AI-классификатор лидов из Telegram.

Определи, является ли сообщение потенциальным клиентским запросом для компании.

ОПИСАНИЕ КОМПАНИИ:
{ABOUT}

КЛЮЧЕВЫЕ ФРАЗЫ:
Они помогают понять тему, но сами по себе не делают сообщение лидом.
{keywords_text}

ПАМЯТЬ С ОЦЕНКАМИ ЧЕЛОВЕКА:
Используй как дополнительный ориентир, но решение принимай по смыслу.
{memory_examples}

КРИТЕРИИ ЛИДА:
lead=true, если сообщение относится к нише и человек явно:
- ищет помощь, специалиста, исполнителя или услугу;
- хочет заказать, оформить, подключить, настроить, получить, исправить или разобраться;
- просит консультацию, расчёт стоимости или спрашивает, кто может помочь;
- описывает проблему и хочет её решить.

lead=false, если:
- сообщение не относится к нише или услугам компании;
- это обычная переписка, ответ, совет, обсуждение или теория;
- есть термины ниши, но нет намерения получить помощь/услугу;
- человек сам что-то объясняет другим;
- сообщение похоже на продолжение чужого диалога;
- по конфигу это явно нецелевой запрос.

Правила:
- оценивай смысл, а не только ключевые слова;
- при сомнении выбирай lead=false;
- отвечай только JSON без markdown.

Формат ответа:
{{
  "lead": true или false,
  "description": "коротко объясни решение"
}}

СООБЩЕНИЕ:
{text}
"""

    try:

        response = ollama.chat(
            model="qwen2.5:7b",
            messages=[
                {
                    "role": "system",
                    "content": "Ты классификатор сообщений."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            format="json"
        )

        raw = response["message"]["content"]
        data = extract_json(raw)

        if not data:
            return None

        result = {
            "lead": bool(data.get("lead", False)),
            "text": text,
            "description": str(data.get("description", "Не указано")),
        }

        return result

    except Exception as e:
        print(
            "❌ Ollama error:",
            e
        )

        return None
