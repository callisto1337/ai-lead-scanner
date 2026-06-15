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
                "text": text
            }


    memory_examples = build_memory_examples()

    keywords_text = format_config_list(
        KEYWORDS,
        "Ключевые фразы не указаны."
    )

    prompt = f"""
Ты универсальный AI-фильтр лидов из Telegram.

Твоя задача — определить, является ли сообщение потенциальным клиентским запросом для компании, услуги или ниши.

Ниша, услуги, целевая аудитория, ограничения и важный контекст описаны в конфиге ниже.
Не используй жёстко заданную отрасль. Работай только по описанию компании, ключевым фразам, памяти и смыслу сообщения.


ОПИСАНИЕ КОМПАНИИ / НИШИ:

{ABOUT}


КЛЮЧЕВЫЕ ФРАЗЫ И ТЕМЫ НИШИ:

Эти фразы помогают понять тематику.
Но наличие ключевой фразы само по себе НЕ означает, что сообщение является лидом.

{keywords_text}


ЧТО СЧИТАТЬ ЛИДОМ:

Сообщение является лидом, если человек в рамках описанной ниши:

- ищет помощь
- ищет исполнителя
- ищет специалиста
- хочет получить услугу
- хочет заказать работу
- хочет купить услугу или решение
- просит консультацию
- просит рассчитать стоимость
- спрашивает, кто может помочь
- описывает проблему и явно хочет её решить
- пишет, что ему что-то нужно сделать, оформить, подключить, настроить, получить, исправить или разобраться


ЧТО НЕ СЧИТАТЬ ЛИДОМ:

Сообщение НЕ является лидом, если это:

- обычная переписка участников чата
- короткий ответ без запроса на услугу
- совет другому человеку
- уточнение внутри текущего диалога
- теоретический вопрос без намерения заказать помощь
- обсуждение темы ниши без клиентского намерения
- сообщение, где человек сам объясняет что-то другому
- вопрос о конкретной кнопке, поле, шаблоне, настройке или действии без просьбы о помощи
- сообщение, похожее на продолжение чужого диалога
- сообщение, где есть только термины из ниши, но нет запроса на услугу
- сообщение не относится к услугам компании из описания
- сообщение относится к тому, чем компания явно НЕ занимается


ПРИМЕРЫ ОБЩЕЙ ЛОГИКИ:

"Нужна помощь с этим вопросом"
lead=true

"Кто может помочь разобраться?"
lead=true

"Ищу специалиста"
lead=true

"Сколько стоит сделать?"
lead=true

"Подскажите, пожалуйста, как это работает?"
lead=false, если нет явного намерения заказать услугу

"По идее да"
lead=false

"Главное, чтобы было правильно заполнено"
lead=false

"Только через шаблон загрузки? Просто выбрать не получится?"
lead=false

"Если через шаблон, где его взять?"
lead=false, если это обычное техническое уточнение в диалоге


ПРИМЕРЫ ИЗ ПАМЯТИ С ОЦЕНКОЙ ЧЕЛОВЕКА:

Используй эти примеры как дополнительный ориентир.
Если новое сообщение похоже на сообщения с lead=false, не считай его лидом.
Если новое сообщение похоже на сообщения с lead=true, считай его лидом.
Но окончательное решение принимай по смыслу сообщения, описанию ниши и правилам выше.

{memory_examples}


ВАЖНЫЕ ПРАВИЛА:

- Анализируй смысл, а не только ключевые слова.
- Ключевые слова нужны только для понимания контекста.
- Лид — это не просто вопрос по теме, а потенциальный клиентский запрос.
- Если человек просто общается, уточняет деталь или отвечает кому-то — это не лид.
- Если человек явно ищет помощь, услугу, специалиста или решение проблемы — это лид.
- Если сообщение подходит под нишу, но нет намерения получить услугу — это не лид.
- Если есть сомнение между lead=true и lead=false, выбирай lead=false.


ОТВЕТ ТОЛЬКО JSON:

{{
  "lead": true или false,
  "reasoning": "Объясни, почему сообщение является или не является лидом, опираясь на описание ниши, ключевые фразы, правила и примеры из памяти"
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
            "text": text
        }


        return result


    except Exception as e:

        print(
            "❌ Ollama error:",
            e
        )

        return None