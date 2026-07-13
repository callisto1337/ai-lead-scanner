from app.db import get_context_chain
from app.model_client import call_model
from app.retrieval import find_similar_messages
from app.settings import MIN_NICHE_SCORE, MIN_INTENT_SCORE

PROMPT_VERSION = "classifier_v5_current_author_intent"


def format_list(items) -> str:
    if not items:
        return "Не указаны"

    if isinstance(items, str):
        return items.strip() or "Не указаны"

    return "\n".join(
        f"- {item}"
        for item in items
        if item
    )


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

    if reply_text:
        reply_block = f"""
СООБЩЕНИЕ, НА КОТОРОЕ ОТВЕЧАЕТ АВТОР:

{reply_text}

Текущее сообщение является ответом на сообщение выше.

Рассматривай оба сообщения вместе:
- reply может содержать тему и описание задачи;
- текущее сообщение может выражать намерение получить помощь;
- не игнорируй reply при расчёте оценок.
""".strip()
    else:
        reply_block = """
REPLY ОТСУТСТВУЕТ.

Не предполагай наличие предыдущих сообщений или скрытого контекста.
""".strip()

    return f"""
РОЛЬ:

Ты анализируешь одно сообщение из общего потока разных Telegram-чатов.

Сообщение может относиться к любой теме.
Название компании, описание ниши и ключевые слова не означают,
что сообщение связано с этой нишей.

Независимо оцени два показателя:

1. niche_score
2. intent_score


ТЕКУЩАЯ НИША:

Компания:
{company_name}

Название:
{niche_name}

Описание услуг:
{about}

Тематические подсказки:
{keywords}

Исключённые направления:
{blacklist}


NICHE_SCORE:

niche_score показывает, насколько тема или задача сообщения
относится к услугам текущей ниши.

Используй только текущее сообщение и reply, если он передан.

Шкала:

0-20 — другая тема или задача не указана.
21-49 — возможна слабая связь, которую приходится додумывать.
50-74 — сообщение тематически близко, но задача описана неясно.
75-89 — тема или задача явно относится к текущей нише.
90-100 — задача напрямую соответствует конкретным услугам текущей ниши.

Правила:

- описание ниши используется только для сравнения;
- описание ниши не является контекстом сообщения;
- ключевые слова являются только тематическими подсказками;
- нельзя переносить информацию из описания ниши в сообщение;
- нельзя додумывать отсутствующую тему или задачу;
- просьба о помощи не повышает niche_score без указания темы;
- упоминание оплаты не повышает niche_score;
- поиск исполнителя не повышает niche_score, если задача неизвестна;
- сообщение, подходящее к любой профессии или услуге, должно получить 0-30;
- запрос по другой нише должен получить низкий niche_score;
- направление из списка исключений должно получить низкий niche_score;
- reply может использоваться для восстановления темы текущего сообщения.


INTENT_SCORE:

intent_score показывает, насколько автор текущего сообщения
сам нуждается в помощи, консультации, обучении, сопровождении
или выполнении задачи.

Оценивай намерение только автора текущего сообщения.

Reply используется для понимания темы и задачи,
но потребность автора reply нельзя переносить
на автора текущего сообщения.

Сначала определи роль текущего сообщения:

- автор задаёт вопрос, просит помощь или описывает нерешённую задачу;
- автор отвечает другому человеку и даёт решение;
- автор предлагает собственные услуги;
- автор сообщает информацию без запроса;
- благодарность, подтверждение или ссылка на предыдущий ответ
  не снижают intent_score, если текущее сообщение содержит новый вопрос;
- уточняющий вопрос о порядке действий, правилах, сроках, схеме
  или изменениях по теме ниши является запросом консультации
  и может получить intent_score 75-89;
- формулировка вопроса как уточнения информации не означает
  отсутствие потребности в помощи.

Высокий intent_score допустим только в первом случае.

Шкала:

0-20 — автор не ищет помощь: отвечает, консультирует, даёт инструкцию,
предлагает свои услуги, сообщает информацию или описывает решённую ситуацию.

21-49 — обсуждение или комментарий без вопроса, собственной задачи
или запроса на консультацию.

50-74 — возможна задача или потребность, но намерение выражено неясно.

75-89 — автор задаёт вопрос по теме ниши, просит совет
или описывает нерешённую проблему.

90-100 — автор прямо ищет помощь, специалиста, обучение,
сопровождение, стоимость услуги или выполнение работы.

Правила:

- конкретный вопрос по теме ниши может получить высокий intent_score;
- вопрос о выборе способа, порядка действий или значения термина
  может быть потенциальным запросом на консультацию;
- автору необязательно прямо искать платную услугу или исполнителя;
- описание ошибки или собственной проблемы может получить высокий intent_score;
- вопрос о стоимости является признаком явного намерения;
- предложение собственных услуг не является потребностью автора;
- поиск сотрудника в штат не является запросом услуги;
- новости, объявления и сообщения без вопроса или нерешённой задачи
  должны получить низкий intent_score;
- наличие темы ниши само по себе не повышает intent_score;
- ответ, рекомендация, инструкция, разъяснение или готовое решение
  должны получить intent_score не выше 20;
- если автор помогает участнику из reply, intent_score должен быть не выше 20,
  даже если reply содержит явную проблему потенциального клиента.


REPLY:

{reply_block}


ТЕКУЩЕЕ СООБЩЕНИЕ:

{text}


ОТВЕТ:

Верни только валидный JSON без markdown и пояснений:

{{
  "niche_score": 0,
  "intent_score": 0,
  "description": "краткое объяснение оценок"
}}

Требования:

- niche_score — целое число от 0 до 100;
- intent_score — целое число от 0 до 100;
- description — одно короткое предложение на русском языке;
- description объясняет связь с нишей и намерение автора;
- не возвращай поле lead;
- не добавляй текст до или после JSON.
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
) -> dict | None:
    prompt = build_prompt(
        text=text,
        niche=niche,
        reply_text=reply_text,
    )

    data = call_model(prompt)

    if not data:
        print("❌ is_lead: call_model returned None", flush=True)
        print(f"TEXT: {text}", flush=True)
        print(f"NICHE: {niche.get('name')}", flush=True)
        return None

    niche_score = normalize_ai_score(
        data.get("niche_score")
    )

    intent_score = normalize_ai_score(
        data.get("intent_score")
    )

    final_lead = (
        niche_score >= MIN_NICHE_SCORE
        and intent_score >= MIN_INTENT_SCORE
    )

    return {
        "lead": final_lead,
        "niche_score": niche_score,
        "intent_score": intent_score,
        "description": data.get("description") or "",
        "raw_response": data,
        "prompt": prompt,
        "prompt_version": PROMPT_VERSION,
    }
