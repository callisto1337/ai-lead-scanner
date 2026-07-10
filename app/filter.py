import time
import json

from app.db import get_context_chain, get_message_by_tg_id
from app.model_client import call_model
from app.retrieval import find_similar_messages
from app.types import TG_MESSAGE_ID
from app.settings import MIN_LEAD_SCORE


def format_config_list(items, fallback="Не указано"):
    if not items:
        return fallback

    return "\n".join(
        f"- {item}"
        for item in items
    )


def build_memory_examples(text: str, niche_id: int):
    rows = find_similar_messages(text, niche_id, 5)

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


def normalize_ai_score(value) -> int:
    try:
        score = int(value)
    except (TypeError, ValueError):
        return 0

    return max(0, min(score, 100))


def is_lead(
    text: str,
    tg_chat_id: int,
    tg_message_id: int,
    niche: dict,
    reply_tg_message_id: TG_MESSAGE_ID | None,
):
    company_name = niche.get("company_name") or "Не указана"
    niche_name = niche.get("name") or "Не указана"
    about = niche.get("about") or "Не указано"

    keywords = "\n".join(niche.get("keywords") or []) or "Не указаны"
    blacklist = "\n".join(niche.get("blacklist") or []) or "Не указан"

    prompt = f"""
Ты AI-классификатор лидов из Telegram.

Твоя задача — определить, является ли автор текущего сообщения потенциальным клиентом компании.

Оценивай только текущее сообщение.
Не додумывай намерения автора.
Не используй внешние знания о бизнесе.
Основывайся только на данных текущей ниши.

КОМПАНИЯ:
{company_name}

НИША:
{niche_name}

ОПИСАНИЕ УСЛУГ:
{about}

КЛЮЧЕВЫЕ ФРАЗЫ:
{keywords}

Ключевые фразы — это только подсказки по тематике.
Они не являются обязательным условием лида.
Совпадение с ключевой фразой само по себе не делает сообщение лидом.

BLACKLIST-ФРАЗЫ:
{blacklist}

ЧТО СЧИТАТЬ ЛИДОМ:

Лид — это сообщение, где автор явно ищет услугу, исполнителя, специалиста, консультацию, сопровождение или платную помощь по текущей нише.

lead=true только если автор:
- ищет исполнителя, специалиста, компанию или подрядчика;
- просит оказать услугу;
- хочет консультацию, сопровождение, настройку, регистрацию или помощь специалиста;
- описывает проблему и явно просит помочь ее решить;
- спрашивает, кто может сделать задачу, связанную с текущей нишей.

lead=false, если автор:
- просто задает вопрос участникам чата;
- спрашивает совет, но не ищет исполнителя;
- отвечает другому человеку;
- дает совет или инструкцию;
- делится опытом;
- обсуждает проблему без запроса на услугу;
- ищет сотрудника в штат;
- рекламирует товары, услуги, каналы, ботов или сторонние предложения;
- пишет про другую сферу, не связанную с текущей нишей;
- сообщение слишком короткое и без контекста невозможно понять намерение.

Главный принцип:
Вопрос по теме не равен лиду.
Проблема по теме не равна лиду.
Лид — это запрос на услугу, специалиста, консультацию или сопровождение.

ШКАЛА SCORE:

0-20:
явный спам, реклама, бот, оффер, другая тема или бессмысленное сообщение.

21-49:
сообщение не является лидом: обычное обсуждение, ответ, совет, жалоба или вопрос без поиска услуги.

50-74:
сообщение связано с тематикой ниши, но нет явного коммерческого намерения или поиска специалиста.

75-89:
вероятный лид: автор ищет помощь, консультацию или специалиста по текущей нише.

90-100:
явный лид: автор прямо ищет исполнителя, услугу, сопровождение, консультацию или решение задачи по текущей нише.

Правило согласованности:
- если score меньше 75, lead должен быть false;
- если score 75 или выше, lead должен быть true;
- если сомневаешься, ставь score ниже 75 и lead=false.

ТЕКУЩЕЕ СООБЩЕНИЕ:
{text}

Ответь только валидным JSON без markdown и без пояснений.

Формат:
{{
  "lead": false,
  "score": 0,
  "description": "короткая причина на русском языке"
}}

Требования:
- lead — boolean;
- score — integer от 0 до 100;
- description — только русский язык;
- description — одно предложение;
- description — максимум 180 символов;
- description кратко объясняет главную причину решения.
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

    score = normalize_ai_score(data.get("score"))

    model_lead = bool(data.get("lead"))

    final_lead = model_lead and score >= MIN_LEAD_SCORE

    return {
        "lead": final_lead,
        "score": score,
        "description": data.get("description", ""),
        "raw_response": json.dumps(data, ensure_ascii=False),
        "prompt": prompt,
    }
