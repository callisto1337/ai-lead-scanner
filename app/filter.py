import ollama
import time
from app.retrieval import find_similar_messages
from app.utils import extract_json, load_lines, load_text

KEYWORDS = load_lines("keywords.txt")
ABOUT = load_text("about.txt")


def format_config_list(items, fallback="Не указано"):
    if not items:
        return fallback

    return "\n".join(
        f"- {item}"
        for item in items
    )


def build_memory_examples(text):
    rows = find_similar_messages(text, 5)

    if not rows:
        return "Пока нет похожих примеров."

    examples = []

    for row in rows:
        ai_lead = "true" if row["ai_lead"] else "false"
        human_lead = "true" if row["human_lead"] else "false"

        examples.append(
            f'- "{row["text"]}" => ai_lead={ai_lead}, human_lead={human_lead} (distance={row["distance"]:.3f})'
        )

    return "\n".join(examples)


def is_lead(text, reply_clean_text: str | None = "Не указано"):
    memory_examples = build_memory_examples(text)

    keywords_text = format_config_list(
        KEYWORDS,
        "Ключевые фразы не указаны."
    )
    reply_text = f"""
КОНТЕКСТ ПЕРЕПИСКИ:

Исходное сообщение:
{reply_clean_text}

Исходное сообщение, используй его только как контекст для понимания текущего сообщения.
Решение (lead=true/false) принимай по текущему сообщению с учетом этого контекста.\n
        """ if reply_clean_text else ""

    prompt = f"""
Ты AI-классификатор лидов из Telegram.

Твоя задача — определить, является ли сообщение потенциальным клиентским запросом для компании.

Ниша, услуги, целевая аудитория и исключения описаны в конфиге ниже.
Не используй внешние знания о бизнесе, если они противоречат описанию компании.

КОНТЕКСТ ИСТОЧНИКА:
Сообщения поступают из разных Telegram-чатов.
Не все участники этих чатов являются потенциальными клиентами.

ОПИСАНИЕ КОМПАНИИ:
{ABOUT}

КЛЮЧЕВЫЕ ФРАЗЫ:
Ключевые фразы помогают определить связь с нишей, но сами по себе НЕ делают сообщение лидом.
{keywords_text}

ПРИМЕРЫ ИЗ ИСТОРИИ РЕШЕНИЙ:
Это похожие сообщения, ранее оцененные человеком. Используй их как дополнительный ориентир.
{memory_examples}

ОПРЕДЕЛЕНИЕ ЛИДА:
lead=true, если сообщение относится к услугам компании и автор явно или неявно ищет помощь, исполнителя, консультацию либо описывает проблему, которую хочет решить.

lead=false если сообщение:
- не относится к услугам компании;
- является обсуждением, рекламой, вакансией, поиском работы или предложением своих услуг;
- не содержит признаков потребности клиента.

ВАЖНО:
- оценивай смысл, а не ключевые слова;
- не придумывай отсутствующий контекст;
- при сомнениях выбирай lead=false.

ФОРМАТ ОТВЕТА:
Ответь только JSON:

{{
 "lead": true/false,
 "description": "одно короткое предложение на русском до 180 символов"
}}

{reply_text}

ТЕКУЩЕЕ СООБЩЕНИЕ:
{text}
"""

    try:

        start_time = time.perf_counter()

        response = ollama.chat(
            model="qwen2.5:7b",
            messages=[
                {
                    "role": "system",
                    "content": "Ты строгий классификатор клиентских запросов. Отвечай только валидным JSON только на русском языке."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            format="json"
        )

        elapsed = time.perf_counter() - start_time
        raw = response["message"]["content"]
        data = extract_json(raw)

        print(
            f"⏱️ ИИ ответил за {elapsed:.2f} сек.",
            flush=True
        )

        print("Prompt tokens:", response["prompt_eval_count"])
        print("Generated tokens:", response["eval_count"])


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
