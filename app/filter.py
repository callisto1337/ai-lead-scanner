import ollama
from pathlib import Path
import time
from memory import load_memory
from utils import normalize, extract_json


BASE_DIR = Path(__file__).parent.parent


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


def build_memory_examples(limit=10):
    memory = load_memory()

    if not memory:
        return "Пока нет примеров обратной связи."

    bad_examples = [
        item for item in memory
        if item.get("feedback") in ("bad", "spam") or item.get("lead") is False
    ]

    good_examples = [
        item for item in memory
        if item.get("feedback") == "good" or item.get("lead") is True
    ]

    selected = bad_examples[-5:] + good_examples[-5:]
    selected = selected[-limit:]

    examples = []

    for item in selected:
        lead_value = "true" if item.get("lead") else "false"
        text = normalize(item.get("text", ""))[:250]

        examples.append(
            f'- "{text}" => lead={lead_value}'
        )

    return "\n".join(examples)


def is_lead(text):

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

Сообщения могут быть из тематических или обычных чатов.
Лид — это запрос на помощь/услугу или вопрос по нише, который может указывать на потребность.

ОПИСАНИЕ КОМПАНИИ:
{ABOUT}

КЛЮЧЕВЫЕ ФРАЗЫ:
Они помогают понять тему, но сами по себе не делают сообщение лидом.
{keywords_text}

ПРИМЕРЫ ОЦЕНКИ:
Используй как ориентир. Особенно учитывай примеры lead=false.
{memory_examples}

КРИТЕРИИ ЛИДА:
lead=true, если сообщение относится к нише и человек:
- ищет помощь, специалиста, исполнителя или услугу;
- хочет заказать, оформить, подключить, настроить, получить, исправить или разобраться;
- просит консультацию, расчёт стоимости или спрашивает, кто может помочь;
- описывает проблему и хочет её решить;
- задаёт вопрос по теме ниши, который может указывать на потребность, проблему, незнание процесса или подготовку к действию;
- спрашивает "как", "что делать", "нужно ли", "куда обратиться", "кто знает", "почему ошибка", "как исправить" в контексте услуг компании.

lead=false, если:
- сообщение не относится к нише или услугам компании;
- это обычная переписка, ответ, совет, флуд или реклама;
- есть термины ниши, но сообщение не содержит вопроса, проблемы или намерения получить помощь/услугу;
- человек сам что-то объясняет другим и не ищет решения для себя;
- сообщение похоже на продолжение чужого диалога без понятного запроса;
- по конфигу это явно нецелевой запрос.

Правила:
- вопрос по теме ниши считай слабым лид-сигналом;
- явный запрос на помощь/услугу считай сильным лид-сигналом;
- если сообщение относится к нише и содержит вопрос или проблему — скорее lead=true;
- если это просто обсуждение без вопроса, проблемы или намерения — lead=false;
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

        start_time = time.perf_counter()

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

        elapsed = time.perf_counter() - start_time

        print(
            f"⏱️ ИИ ответил за {elapsed:.2f} сек.",
            flush=True
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
