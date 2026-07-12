from app.db import get_context_chain
from app.model_client import call_model
from app.retrieval import find_similar_messages
from app.settings import MIN_NICHE_SCORE, MIN_INTENT_SCORE

PROMPT_VERSION = "classifier_v2_niche_intent"


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
Название компании, описание ниши и ключевые слова не означают, что сообщение связано с этой нишей.

Тебе нужно независимо оценить два показателя:

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

niche_score показывает, насколько тема или задача сообщения относится к услугам текущей ниши.

Оцени только информацию из текущего сообщения и reply, если он передан.

Шкала:

0-20 — сообщение относится к другой теме или задача не указана.
21-49 — возможна слабая связь, которую приходится додумывать.
50-74 — сообщение тематически близко, но задача описана неясно.
75-89 — задача явно относится к текущей нише.
90-100 — задача напрямую соответствует конкретным услугам текущей ниши.

Правила:

- описание ниши используется только для сравнения;
- описание ниши не является контекстом сообщения;
- ключевые слова являются только тематическими подсказками;
- нельзя переносить информацию из описания ниши в сообщение;
- нельзя додумывать отсутствующую тему или задачу;
- если сообщение подходит к любой профессии или услуге, niche_score должен быть от 0 до 30;
- просьба о помощи не повышает niche_score без указания темы;
- упоминание оплаты не повышает niche_score;
- поиск исполнителя не повышает niche_score, если его задача неизвестна;
- запрос по другой нише должен получить низкий niche_score;
- направление из списка исключений должно получить низкий niche_score.


INTENT_SCORE:

intent_score показывает, насколько автору требуется помощь, решение задачи,
консультация, обучение, сопровождение или выполнение работы.

Оценивай потребность автора независимо от текущей ниши.

Шкала:

0-20 — у автора нет задачи или потребности в помощи.
21-49 — обсуждение, новость, комментарий, реклама, предложение собственных услуг или ответ другому человеку.
50-74 — тема или проблема упомянута, но потребность автора неочевидна.
75-89 — автор задаёт конкретный вопрос, описывает свою проблему или нуждается в консультации.
90-100 — автор явно ищет решение, помощь, специалиста, обучение, сопровождение или выполнение задачи.

Правила:

- конкретный вопрос по собственной задаче может получить высокий intent_score;
- описание ошибки или проблемы может получить высокий intent_score;
- автору необязательно прямо писать о платной услуге или поиске исполнителя;
- вопрос должен описывать реальную задачу, которую можно решить услугами текущей ниши;
- общий интерес к теме, новости и теоретические вопросы не означают потребность в помощи;
- предложение собственных услуг не является потребностью автора;
- поиск сотрудника в штат не является запросом услуги.

Оценивай намерение только автора текущего сообщения.

Общий вопрос об определении термина без описания собственной ситуации,
задачи или планов не считается потребностью в услуге.

Reply используется для понимания темы, но не передаёт текущему автору
намерение другого участника.

Если автор текущего сообщения предлагает свои услуги, помощь,
консультацию или просит написать ему, intent_score должен быть 0-20,
даже если в reply другой человек описывает проблему.

Фразы от первого лица о готовности выполнить работу:
«занимаюсь», «делаю», «могу помочь», «обращайтесь», «пишите мне»
означают предложение услуги, а не потребность в помощи.


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
