import time

from app.db import get_context_chain, get_message_by_tg_id
from app.model_client import call_model
from app.retrieval import find_similar_messages
from app.types import TG_MESSAGE_ID
from app.utils import load_lines, load_text

KEYWORDS = load_lines("keywords.txt")
ABOUT = load_text("about.txt")


def format_config_list(items, fallback="Не указано"):
    if not items:
        return fallback

    return "\n".join(
        f"- {item}"
        for item in items
    )


def build_memory_examples(text: str):
    rows = find_similar_messages(text, 5)

    if not rows:
        return "Пока нет похожих примеров."

    examples = []

    for row in rows:
        ai_lead = "true" if row["ai_lead"] else "false"
        human_lead = "true" if row["human_lead"] else "false"

        chain = get_context_chain(
            tg_chat_id=row.get("tg_chat_id"),
            tg_message_id=row.get("tg_message_id"),
            reply_to_id=row.get("reply_to_id"),
        )

        if not chain:
            continue

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
    reply_tg_message_id: TG_MESSAGE_ID | None
):
    memory_examples = build_memory_examples(text)
    reply_message_id = get_message_by_tg_id(reply_tg_message_id)
    keywords_text = format_config_list(
        KEYWORDS,
        "Ключевые фразы не указаны."
    )
    context_chain = get_context_chain(
        tg_chat_id=tg_chat_id,
        tg_message_id=tg_message_id,
        reply_to_id=reply_message_id
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

    print("PROMPT: ", prompt, flush=True)

    start_time = time.perf_counter()
    data = call_model(prompt)
    elapsed = time.perf_counter() - start_time

    print(
        f"⏱️ ИИ ответил за {elapsed:.2f} сек.",
        flush=True
    )

    if not data:
        return None

    result = {
        "lead": bool(data.get("lead", False)),
        "text": text,
        "description": str(data.get("description", "Не указано")),
    }

    return result
