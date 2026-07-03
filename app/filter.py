import ollama
import time

from app.db import get_message_by_id, get_context_chain
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


def build_message_chain(message_id, depth=5):
    chain = []
    current_id = message_id

    while current_id and len(chain) < depth:
        row = get_message_by_id(current_id)

        if not row:
            break

        chain.append(row["text"])
        current_id = row["reply_to_id"]

    chain.reverse()

    return chain


def build_memory_examples(text):
    rows = find_similar_messages(text, 5)

    if not rows:
        return "Пока нет похожих примеров."

    examples = []

    for row in rows:
        ai_lead = "true" if row["ai_lead"] else "false"
        human_lead = "true" if row["human_lead"] else "false"

        chain = build_message_chain(row["id"])

        example = []

        if len(chain) > 1:
            example.append("Контекст диалога:")

            for msg in chain[:-1]:
                example.append(f"- {msg}")

        example.append(f'Сообщение: "{chain[-1]}"')

        example.append(
            f"Результат: ai_lead={ai_lead}, human_lead={human_lead}"
        )

        examples.append("\n".join(example))

    return "\n\n".join(examples)


def is_lead(
    text: str,
    tg_chat_id: int,
    tg_message_id: int,
    reply_tg_message_id: int | None
):
    memory_examples = build_memory_examples(text)
    keywords_text = format_config_list(
        KEYWORDS,
        "Ключевые фразы не указаны."
    )
    context_chain = get_context_chain(
        tg_chat_id=tg_chat_id,
        tg_message_id=tg_message_id,
        reply_to_tg_message_id=reply_tg_message_id
    )

    context_block = ""

    if len(context_chain) > 1:
        context_block = f"""
КОНТЕКСТ ДИАЛОГА
Ниже приведены предыдущие сообщения этой ветки:

{chr(10).join(f"- {m}" for m in context_chain[:-1])}

Используй их только для понимания смысла последнего сообщения.
""" if len(context_chain) else ""

    prompt = f"""
Ты AI-классификатор лидов из Telegram.

Твоя задача — определить, является ли автор текущего сообщения потенциальным клиентом компании.
Не используй внешние знания о бизнесе. Основывайся только на описании компании, сообщении, контексте диалога и примерах из истории.

ОПИСАНИЕ КОМПАНИИ:
{ABOUT}

КЛЮЧЕВЫЕ ФРАЗЫ:
Ключевые фразы помогают определить тематику сообщения, но сами по себе НЕ являются признаком лида.
{keywords_text}

ПРИМЕРЫ ИЗ ИСТОРИИ:
Ниже приведены похожие диалоги, ранее оценённые человеком.
Используй их как дополнительный ориентир.
Если текущая ситуация похожа на один из примеров, учитывай это при принятии решения.
Если пример противоречит описанию компании — следуй описанию компании.

{memory_examples}
{context_block}
ОПРЕДЕЛЕНИЕ ЛИДА
lead=true, если по текущему сообщению (с учетом контекста диалога) можно сделать вывод, что автор является потенциальным клиентом компании.

Обычно это означает, что автор:
- ищет помощь;
- ищет исполнителя или специалиста;
- хочет решить проблему;
- задаёт практический вопрос по услугам компании;
- хочет заказать, оформить, подключить, настроить, исправить или разобраться;
- описывает ситуацию, из которой следует возможная потребность в услугах компании.

lead=false, если:
- сообщение не относится к услугам компании;
- это обычное обсуждение, мнение, спор или переписка без клиентской потребности;
- автор отвечает другому участнику, но сам не проявляет интерес к услугам компании;
- автор предлагает свои услуги, рекламирует себя, товар, сервис, канал или бота;
- автор ищет сотрудников, исполнителей для своей вакансии или работу;
- информации недостаточно, чтобы уверенно считать автора потенциальным клиентом.

ПРАВИЛА
- Оценивай смысл сообщения, а не отдельные слова.
- Контекст диалога нужен только для понимания текущего сообщения.
- Решение всегда принимай по ТЕКУЩЕМУ сообщению.
- Примеры из истории являются ориентиром, а не обязательным шаблоном.
- Не придумывай факты, которых нет в сообщении.
- Если сомневаешься — выбирай lead=false.

ФОРМАТ ОТВЕТА
Ответь только JSON.

{{
  "lead": true или false,
  "description": "одно короткое предложение на русском языке, максимум 180 символов"
}}

ТРЕБОВАНИЯ К description:
- только русский язык;
- одно предложение;
- кратко объясни главную причину решения;
- не пересказывай инструкцию.

ТЕКУЩЕЕ СООБЩЕНИЕ:
{text}
"""

    print("PROMT: ", prompt, flush=True)

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
