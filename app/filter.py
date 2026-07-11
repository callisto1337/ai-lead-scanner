import json

from app.db import get_context_chain
from app.model_client import call_model
from app.retrieval import find_similar_messages
from app.settings import MIN_LEAD_SCORE


PROMPT_VERSION = "lead_classifier_v2_algorithm"


def format_list(items) -> str:
    if not items:
        return "Не указаны"

    if isinstance(items, str):
        return items.strip() or "Не указаны"

    return "\n".join(f"- {item}" for item in items if item)


def build_prompt(
    text: str,
    niche: dict,
    reply_text: str | None = None,
) -> str:
    company_name = niche.get("company_name") or "Не указана"
    niche_name = niche.get("name") or "Не указана"

    about = niche.get("about") or "Не указано"
    keywords = format_list(niche.get("keywords") or [])
    blacklist = format_list(niche.get("blacklist") or [])

    reply_block = ""

    if reply_text:
        reply_block = f"""
СООБЩЕНИЕ, НА КОТОРОЕ ОТВЕЧАЕТ АВТОР:
{reply_text}

ВАЖНО ПО REPLY:
Текущее сообщение является ответом на сообщение выше.
Используй reply только для понимания смысла короткого ответа.
Если без reply текущее сообщение слишком общее, но reply явно связан с текущей нишей, можно учитывать их вместе.
Если reply отсутствует, не предполагай скрытый контекст.
Если текущее сообщение — совет, комментарий, рекомендация или ответ другому человеку, а не собственный запрос автора на услугу, ставь lead=false и score ниже {MIN_LEAD_SCORE}.
"""

    return f"""
PROMPT_VERSION:
{PROMPT_VERSION}

РОЛЬ:
Ты AI-классификатор лидов из Telegram.

ЗАДАЧА:
Определи, является ли автор текущего сообщения потенциальным клиентом компании по текущей нише.

ОГРАНИЧЕНИЯ:
- Не используй внешние знания.
- Не додумывай намерения автора.
- Основывайся только на данных текущей ниши и текущем сообщении.
- Ключевые фразы — только подсказки по тематике, а не доказательство лида.
- Совпадение с ключевой фразой само по себе не делает сообщение лидом.

КОМПАНИЯ:
{company_name}

НИША:
{niche_name}

ОПИСАНИЕ УСЛУГ:
{about}

КЛЮЧЕВЫЕ ФРАЗЫ:
{keywords}

BLACKLIST-ФРАЗЫ:
{blacklist}

АЛГОРИТМ РЕШЕНИЯ:

1. Проверь связь сообщения с текущей нишей.

Сообщение должно быть связано с текущей нишей по смыслу, а не обязательно точными словами из описания или keywords.

Если связь с нишей явная — продолжай оценку.
Если связь слабая, непонятная или относится к другой сфере — lead=false, score 0-30.

Общие фразы без указания задачи или темы не являются лидом:
"кто может помочь?", "кто поможет платно?", "нужна помощь", "напишите в личку", "есть специалист?".
Без связи с текущей нишей такие сообщения оценивай как lead=false.

2. Проверь blacklist и явный мусор.
Если сообщение похоже на рекламу, оффер, спам, поиск сотрудника, предложение работы, продажу сторонних услуг, совет или ответ другому человеку — lead=false, score 0-40.

3. Проверь наличие коммерческого намерения.
Лидом считается только сообщение, где автор сам явно ищет исполнителя, специалиста, компанию, консультацию, сопровождение или платную помощь по текущей нише.

4. Отличай проблему от запроса на услугу.
Если автор пишет “ошибка”, “проблема”, “что делать”, “подскажите”, “кто сталкивался”, но не говорит, что ищет специалиста, исполнителя, услугу, консультацию или платную помощь — это НЕ лид.

Такие сообщения оценивай как тематический вопрос: lead=false, score 50-74.

5. Высокий score ставь только при явном запросе на помощь специалиста.
score 80+ можно ставить только если одновременно выполнены два условия:

1. Понятно, что задача относится к текущей нише.
2. Автор явно ищет специалиста, исполнителя, услугу, консультацию, сопровождение или платную помощь.

Если есть только просьба о помощи, но непонятно по какой задаче — lead=false, score 0-40.
Если есть только тематический вопрос, но нет поиска услуги — lead=false, score 50-74.

6. Определи score:
0-20 — явный спам, реклама, бот, оффер, другая тема или бессмысленное сообщение.
21-49 — не лид: обсуждение, ответ, совет, жалоба или вопрос без поиска услуги.
50-74 — сообщение связано с нишей, но нет явного коммерческого намерения.
75-79 — слабый лид: есть намек на поиск помощи, но коммерческое намерение выражено нечетко.
80-89 — вероятный лид: автор явно ищет специалиста, консультацию, услугу или платную помощь по текущей нише.
90-100 — явный лид: автор прямо ищет исполнителя, компанию, услугу, сопровождение или платное решение задачи по текущей нише.

7. Прими финальное решение.
Если score меньше {MIN_LEAD_SCORE}, lead=false.
Если score {MIN_LEAD_SCORE} или выше, lead=true.
Если есть сомнение — lead=false и score ниже {MIN_LEAD_SCORE}.

ГЛАВНЫЙ ПРИНЦИП:
Вопрос по теме не равен лиду.
Проблема по теме не равна лиду.
Фразы “ошибка”, “проблема”, “что делать”, “подскажите” сами по себе не являются запросом на услугу.
Лид — это запрос на услугу, специалиста, консультацию или сопровождение именно по текущей нише.

{reply_block}

ТЕКУЩЕЕ СООБЩЕНИЕ:
{text}

ОТВЕТ:
Верни только валидный JSON без markdown и без пояснений.

Формат:
{{
  "lead": false,
  "score": 0,
  "description": "короткая причина на русском языке"
}}

ТРЕБОВАНИЯ К JSON:
- lead — boolean;
- score — integer от 0 до 100;
- description — только русский язык;
- description — одно предложение;
- description — максимум 180 символов;
- description кратко объясняет главную причину решения.
""".strip()


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
    reply_tg_message_id: int | None = None,
    reply_text: str | None = None,
):
    prompt = build_prompt(
        text=text,
        niche=niche,
        reply_text=reply_text,
    )

    print("PROMPT:", prompt, flush=True)

    data = call_model(prompt)

    if not data:
        return None

    score = normalize_ai_score(data.get("score"))
    model_lead = bool(data.get("lead"))

    final_lead = model_lead and score >= MIN_LEAD_SCORE

    data["score"] = score
    data["lead"] = final_lead

    return {
        "lead": final_lead,
        "score": score,
        "description": data.get("description", ""),
        "raw_response": json.dumps(data, ensure_ascii=False),
        "prompt": prompt,
        "prompt_version": PROMPT_VERSION,
    }