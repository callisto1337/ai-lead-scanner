import json
import ollama
from pathlib import Path
import re


BASE_DIR = Path(__file__).parent


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


# ---------------- MEMORY ----------------

def load_memory():
    path = BASE_DIR / "config" / "memory.json"

    if not path.exists():
        return []

    try:
        return json.loads(
            path.read_text(encoding="utf-8")
        )
    except:
        return []


def save_memory(item):
    path = BASE_DIR / "config" / "memory.json"

    memory = load_memory()

    memory.append(item)

    memory = memory[-200:]

    path.write_text(
        json.dumps(
            memory,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


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


def build_memory_examples(limit=20):
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
category={item.get("category", "другое")}
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
                "category": "другое",
                "text": text
            }


    memory_examples = build_memory_examples()

    prompt = f"""
Ты AI-фильтр лидов из Telegram.

Определи, является ли сообщение потенциальным клиентом.


КОМПАНИЯ:

{ABOUT}


ПРИМЕРЫ ИЗ ПАМЯТИ С ОЦЕНКОЙ ЧЕЛОВЕКА:

Используй эти примеры как дополнительный ориентир.
Если новое сообщение похоже на сообщения с lead=false, не считай его лидом.
Если новое сообщение похоже на сообщения с lead=true, считай его лидом.
Но окончательное решение принимай по смыслу сообщения.

{memory_examples}


КОМПАНИЯ РАБОТАЕТ С:

- Честный знак
- Маркировка товаров
- Коды маркировки
- DataMatrix
- Регистрация в системе
- Обучение работе с маркировкой


ЛИД:

Человек:

- ищет помощь
- ищет исполнителя
- хочет получить услугу
- спрашивает как сделать
- хочет решить проблему


Примеры:

"Нужны коды маркировки"
lead=true

"Кто поможет с ЧЗ"
lead=true

"Кто обучит работе в Честном знаке"
lead=true

"Как зарегистрироваться"
lead=true


НЕ ЛИД:

"Нужен бухгалтер"
lead=false

"Ищу юриста"
lead=false

"Кто сделает сайт"
lead=false


ВАЖНО:

- анализируй смысл
- не ориентируйся только на ключевые слова
- если человек ищет решение по маркировке — это лид
- запросы про покупку кодов тоже считать лидом


КАТЕГОРИЯ:

Выбери одно:

Регистрация
Коды маркировки
Маркировка товара
Обучение
Консультация
Другое


ОТВЕТ ТОЛЬКО JSON:

{{
"lead": true или false,
"category": "категория из списка выше"
}}


СООБЩЕНИЕ:

{text}
"""


    try:

        response = ollama.chat(
            model="qwen2.5:14b",
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

        print("RAW:", raw)


        data = extract_json(raw)


        if not data:
            return None


        result = {

            "lead": bool(data.get("lead", False)),

            "category": data.get(
                "category",
                "другое"
            ),

            "text": text

        }


        return result


    except Exception as e:

        print(
            "❌ Ollama error:",
            e
        )

        return None