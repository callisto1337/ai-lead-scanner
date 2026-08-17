import concurrent.futures
from typing import Any

from app.metrics import ai_errors
from app.model_client import (
    INTENT_OUTPUT_SCHEMA,
    NICHE_OUTPUT_SCHEMA,
    call_model,
)
from app.retrieval import find_similar_messages
from app.settings import NICHE_EXAMPLES_ENABLED
from app.types import IsLeadResult, NicheId, NicheWithConfig

NICHE_PROMPT_VERSION = "niche_v1"
INTENT_PROMPT_VERSION = "intent_v1"

MATCH_VALUES = {"да", "нет", "спорно"}


def format_list(items: list[str]) -> str:
    if not items:
        return "Не указаны"

    if isinstance(items, str):
        return items.strip() or "Не указаны"

    return "\n".join(
        f"- {item}"
        for item in items
        if item
    )


def build_memory_examples(
    text: str,
    niche_id: NicheId,
    limit: int = 6,
) -> str:
    try:
        rows = find_similar_messages(
            text=text,
            niche_id=niche_id,
            limit=limit,
        )
    except Exception as error:
        print(
            (
                "⚠️ Не удалось получить похожие примеры: "
                f"{type(error).__name__}: {error}"
            ),
            flush=True,
        )
        return "Похожих примеров с оценкой человека нет."

    if not rows:
        return "Похожих примеров с оценкой человека нет."

    examples: list[str] = []

    for index, row in enumerate(rows, start=1):
        human_assessment = (
            "true"
            if row["human_lead"]
            else "false"
        )

        example_lines = [
            f"Пример {index}:",
            f'Сообщение CURRENT_USER: "{row["text"]}"',
        ]

        reply_text = row["reply_text"]

        if reply_text:
            example_lines.extend(
                [
                    (
                        "Связь CURRENT_USER и REPLY_USER: "
                        f'{row["reply_author_relation"]}'
                    ),
                    f'Сообщение REPLY_USER: "{reply_text}"',
                ]
            )
        else:
            example_lines.append(
                "Сообщение REPLY_USER: отсутствует"
            )

        example_lines.extend(
            [
                f"Оценка человека: {human_assessment}",
                f"Расстояние: {row['distance']:.4f}",
            ]
        )

        examples.append(
            "\n".join(example_lines)
        )

    return "\n\n".join(examples)


NICHE_STATIC_RULES = """
РОЛЬ:

Ты сотрудник компании, который проверяет, относится ли сообщение
из Telegram-чата к услугам компании.


ЗАДАЧА:

Проанализируй одно сообщение CURRENT_USER.

Сообщение может относиться к любой теме.
Название компании, описание ниши и ключевые слова не означают,
что сообщение связано с этой нишей.

Определи одну категорию: niche_match.


ОБОЗНАЧЕНИЯ ПОЛЬЗОВАТЕЛЕЙ:

CURRENT_USER — автор текущего сообщения.
REPLY_USER — автор сообщения, на которое отвечает CURRENT_USER.
REPLY_USER может быть тем же человеком или другим человеком.

Информация о связи между CURRENT_USER и REPLY_USER является достоверной.
Не пытайся определять авторство самостоятельно по тексту.

Если авторство REPLY_USER неизвестно, считай его другим человеком.


NICHE_MATCH:

niche_match показывает, относится ли тема или задача сообщения CURRENT_USER
к услугам текущей ниши.

Для определения темы используй сообщение CURRENT_USER
и сообщение REPLY_USER, если оно передано.

Категории:

да — сообщение упоминает или обсуждает конкретную тему, объект, процесс
или услугу из списка ниши — независимо от того, задан вопрос, дан ответ
или сделано утверждение.

спорно — связь с нишей есть, но неясная: тема упомянута только через
тематические подсказки, общий контекст чата или частичное сходство,
без явного указания на конкретный процесс, объект или услугу ниши.

нет — другая тема, либо тема не указана вовсе, либо сообщение
подходит к любой профессии или услуге без конкретики.

Правила:

- описание ниши используется только для сравнения и не является
  контекстом сообщения;
- ключевые слова являются только тематическими подсказками;
- нельзя переносить информацию из описания ниши в сообщение CURRENT_USER;
- нельзя додумывать отсутствующую тему;
- упоминание оплаты не даёт "да";
- запрос по другой нише должен получить "нет";
- направление из списка исключений должно получить "нет";
- совпадение с нишей должно опираться на отличительные термины ниши
  (тематические подсказки, конкретные названия систем и процессов
  из описания услуг), а не на обычные слова, которые используются
  и в других системах (например, "кабинет", "остатки", "склад", "коды",
  "отчёт" сами по себе, без явной привязки к теме ниши);
- если такое общее слово встречается без явной привязки именно к теме
  ниши — это не даёт "да", максимум "спорно"; а если по контексту ясно,
  что речь о другой системе — "нет", даже при формальном совпадении
  отдельных слов;
- "да" допустимо только тогда, когда сообщение CURRENT_USER
  содержит конкретную тему, объект, процесс или услугу,
  которые можно напрямую сопоставить с услугами ниши;
- если CURRENT_USER и REPLY_USER — один и тот же человек,
  сообщение REPLY_USER может восстановить пропущенную часть
  темы сообщения CURRENT_USER;
- если REPLY_USER — другой человек, его сообщение можно использовать
  только для уточнения смысла уже имеющихся слов и ссылок
  в сообщении CURRENT_USER;
- тема, присутствующая только в сообщении REPLY_USER,
  не позволяет выставить "да" — максимум "спорно";
- если связь с нишей строится только на общих словах, тематических
  подсказках, предполагаемом контексте чата или описании услуг —
  максимум "спорно";
- если сообщение CURRENT_USER можно полностью понять без обращения
  к услугам текущей ниши, нельзя додумывать связь с ней.


ФОРМАТ ОТВЕТА:

Верни только валидный JSON без markdown и пояснений:

{
  "niche_match": "да",
  "description": "краткое объяснение на русском языке"
}

Требования:

- niche_match — одно из значений: "да", "нет", "спорно";
- description — одно короткое предложение на русском языке,
  объясняющее связь сообщения CURRENT_USER с нишей;
- не добавляй текст до или после JSON;
- description не должно утверждать наличие темы или задачи,
  которых нет в сообщении CURRENT_USER или сообщении REPLY_USER.
""".strip()


INTENT_STATIC_RULES = """
РОЛЬ:

Ты сотрудник компании, который определяет, ищет ли автор сообщения
помощь для решения собственной задачи.


ЗАДАЧА:

Проанализируй одно сообщение CURRENT_USER.

Определи одну категорию: intent_match — показывает, насколько
CURRENT_USER сам нуждается в помощи, консультации, обучении,
сопровождении или выполнении задачи.

Оценивай намерение только CURRENT_USER.


ОБОЗНАЧЕНИЯ ПОЛЬЗОВАТЕЛЕЙ:

CURRENT_USER — автор текущего сообщения.
REPLY_USER — автор сообщения, на которое отвечает CURRENT_USER.
REPLY_USER может быть тем же человеком или другим человеком.

Информация о связи между CURRENT_USER и REPLY_USER является достоверной.
Не пытайся определять авторство самостоятельно по тексту.

Если авторство REPLY_USER неизвестно, считай его другим человеком.


INTENT_MATCH:

Сначала определи коммуникативную роль сообщения CURRENT_USER:

- CURRENT_USER описывает собственную нерешённую задачу;
- CURRENT_USER просит помощь, консультацию или выполнение работы для себя;
- CURRENT_USER отвечает REPLY_USER;
- CURRENT_USER помогает диагностировать ситуацию REPLY_USER;
- CURRENT_USER даёт совет, инструкцию, решение или разъяснение;
- CURRENT_USER обсуждает или комментирует чужую ситуацию;
- CURRENT_USER сообщает о совершённом действии или продолжении общения;
- CURRENT_USER предлагает собственные услуги;
- CURRENT_USER сообщает информацию без собственного запроса.

"да" допустимо только тогда, когда CURRENT_USER выражает собственную
нерешённую потребность.

Наличие вопроса или просьбы в сообщении REPLY_USER
не является доказательством потребности CURRENT_USER.


СВЯЗЬ CURRENT_USER И REPLY_USER:

Если CURRENT_USER и REPLY_USER — один и тот же человек:

- сообщение REPLY_USER может содержать предыдущую часть
  собственной задачи CURRENT_USER;
- оценивай оба сообщения как продолжение одной мысли;
- короткое уточнение, вопрос о стоимости, порядке действий, сроках,
  последствиях или инструкции может получить "да";
- благодарность или подтверждение не мешают "да",
  если после них CURRENT_USER задаёт новый вопрос;
- описание собственной нерешённой проблемы в сообщении REPLY_USER
  можно учитывать при оценке намерения CURRENT_USER.

Если REPLY_USER — другой человек:

- сообщение REPLY_USER используется только для определения темы разговора;
- нельзя переносить вопрос, проблему, намерение или потребность
  REPLY_USER на CURRENT_USER;
- сначала проверь, является ли сообщение CURRENT_USER ответом,
  советом, решением, разъяснением, уточнением ситуации REPLY_USER
  или действием в пользу REPLY_USER;
- если сообщение CURRENT_USER можно разумно понять как помощь REPLY_USER,
  выбирай эту интерпретацию, пока CURRENT_USER явно
  не обозначил собственную проблему;
- диагностический или уточняющий вопрос CURRENT_USER,
  заданный для выяснения деталей или помощи REPLY_USER,
  является частью помощи REPLY_USER и должен получить "нет";
- реакция, комментарий или продолжение обсуждения ситуации REPLY_USER
  без попытки помочь и без собственной задачи CURRENT_USER — "спорно";
- если нельзя уверенно определить, относится ли вопрос
  к собственной задаче CURRENT_USER или к ситуации REPLY_USER — "спорно";
- сообщение о том, что CURRENT_USER связался с другим участником,
  продолжил общение в другом месте или уже совершил некоторое действие,
  само по себе не является запросом услуги;
- краткое указание, что следует сделать, является решением или советом,
  а не собственной задачей CURRENT_USER;
- ответ, совет, инструкция, готовое решение, диагностика или разъяснение
  должны получить "нет";
- "да" возможно только тогда, когда CURRENT_USER
  явно описывает собственную аналогичную задачу, просит решение для себя,
  ищет исполнителя или запрашивает консультацию для своего случая.

Признаки ответа, диагностики или консультации REPLY_USER:

- CURRENT_USER объясняет, как следует поступить;
- CURRENT_USER рекомендует конкретные действия;
- CURRENT_USER сообщает правило, факт или правильный порядок действий;
- CURRENT_USER подтверждает или опровергает информацию;
- CURRENT_USER предлагает вариант решения;
- CURRENT_USER описывает, что должен сделать REPLY_USER;
- CURRENT_USER запрашивает данные, необходимые для разбора
  ситуации REPLY_USER;
- CURRENT_USER уточняет параметры проблемы REPLY_USER;
- CURRENT_USER сообщает о выполненном действии
  без нового собственного запроса.

Такие сообщения должны получить "нет",
даже если сообщение REPLY_USER содержит явную проблему
потенциального клиента.

Категории:

да — CURRENT_USER прямо ищет специалиста или исполнителя, просит
оказать услугу, запрашивает стоимость, сроки или условия выполнения
работы для себя, либо явно описывает собственную нерешённую задачу
и просит совет по своему случаю.

спорно — CURRENT_USER реагирует, комментирует или продолжает
обсуждение чужой ситуации, выражает неясный интерес либо возможную,
но не подтверждённую собственную задачу; либо описывает свою
ситуацию, но потребность в помощи выражена неясно.

нет — CURRENT_USER не ищет помощь: отвечает, консультирует,
диагностирует, даёт инструкцию, задаёт диагностический
или уточняющий вопрос для помощи REPLY_USER, предлагает
собственные услуги, сообщает информацию или описывает уже
совершённое действие.

Правила:

- конкретный вопрос может получить "да", только если относится
  к собственной ситуации CURRENT_USER;
- вопрос о выборе способа, порядке действий, правилах, сроках,
  последствиях, инструкции или значении термина
  может быть запросом на консультацию;
- уточняющий вопрос может получить "да",
  только если относится к собственной задаче CURRENT_USER;
- CURRENT_USER необязательно прямо искать платную услугу или исполнителя;
- описание ошибки или собственной проблемы CURRENT_USER
  может получить "да";
- вопрос о стоимости является признаком явного намерения,
  если стоимость интересует CURRENT_USER;
- предложение собственных услуг не является потребностью CURRENT_USER;
- поиск сотрудника в штат не является запросом услуги;
- новости и объявления без вопроса или нерешённой задачи — "нет";
- нельзя считать любое сообщение с вопросительным знаком
  запросом на услугу;
- нельзя считать любой вопрос собственной потребностью CURRENT_USER.


ФОРМАТ ОТВЕТА:

Верни только валидный JSON без markdown и пояснений:

{
  "intent_match": "да",
  "description": "краткое объяснение на русском языке"
}

Требования:

- intent_match — одно из значений: "да", "нет", "спорно";
- description — одно короткое предложение на русском языке,
  объясняющее коммуникативную роль CURRENT_USER;
- если CURRENT_USER отвечает, консультирует или диагностирует
  ситуацию REPLY_USER, description должно прямо это отражать;
- не добавляй текст до или после JSON;
- description не должно приписывать CURRENT_USER
  проблему или потребность REPLY_USER.
""".strip()


def build_reply_block(
    reply_text: str | None,
    reply_author_relation: str | None,
) -> str:
    if reply_text:
        return f"""
Связь CURRENT_USER и REPLY_USER:
{reply_author_relation}

Сообщение REPLY_USER:
{reply_text}
        """.strip()

    return "Сообщение REPLY_USER отсутствует."


def build_niche_prompt(
    text: str,
    niche: NicheWithConfig,
    reply_text: str | None = None,
    reply_author_relation: str | None = None,
    memory_examples: str | None = None,
) -> str:
    company_name = niche.get("company_name") or "Не указана"
    niche_name = niche.get("name") or "Не указана"
    about = niche.get("about") or "Не указано"
    keywords = format_list(niche.get("keywords") or [])
    blacklist = format_list(niche.get("blacklist") or [])

    reply_block = build_reply_block(reply_text, reply_author_relation)

    examples_block = (
        f"""

ПРИМЕРЫ С ОЦЕНКОЙ ЧЕЛОВЕКА:

{memory_examples}
"""
        if memory_examples
        else ""
    )

    return f"""{NICHE_STATIC_RULES}


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


СООБЩЕНИЕ REPLY_USER:

{reply_block}


СООБЩЕНИЕ CURRENT_USER:

{text}
{examples_block}

ОТВЕТ:
"""


def build_intent_prompt(
    text: str,
    reply_text: str | None = None,
    reply_author_relation: str | None = None,
) -> str:
    reply_block = build_reply_block(reply_text, reply_author_relation)

    return f"""{INTENT_STATIC_RULES}


СООБЩЕНИЕ REPLY_USER:

{reply_block}


СООБЩЕНИЕ CURRENT_USER:

{text}


ОТВЕТ:
"""


def build_tracing_context(
    niche: NicheWithConfig,
    prompt_version: str,
) -> tuple[dict[str, str], list[str]]:
    company_name = str(niche.get("company_name") or "Не указана").strip() or "Не указана"
    niche_name = str(niche.get("name") or "Не указана").strip() or "Не указана"
    niche_slug = str(niche.get("slug") or "").strip()

    metadata: dict[str, str] = {
        "company_id": str(niche["company_id"]),
        "company_name": company_name,
        "niche_id": str(niche["id"]),
        "niche_name": niche_name,
        "promptversion": prompt_version,
    }

    if niche_slug:
        metadata["niche_slug"] = niche_slug

    niche_label = f"{company_name} / {niche_name}"
    tag_value = f"niche:{niche_label}"[:200]
    tags = [tag_value]

    return metadata, tags


def combine_verdict(niche_match: str, intent_match: str) -> str:
    if niche_match == "нет" or intent_match == "нет":
        return "not_lead"

    if niche_match == "да" and intent_match == "да":
        return "lead"

    if niche_match == "спорно" and intent_match == "спорно":
        return "not_lead"

    return "borderline"


def _call_niche_model(
    prompt: str,
    metadata: dict[str, str],
    tags: list[str],
) -> dict[str, Any] | None:
    return call_model(
        prompt,
        output_schema=NICHE_OUTPUT_SCHEMA,
        schema_name="niche-classification",
        span_name="niche-classification",
        metadata=metadata,
        tags=tags,
    )


def _call_intent_model(
    prompt: str,
    metadata: dict[str, str],
    tags: list[str],
) -> dict[str, Any] | None:
    return call_model(
        prompt,
        output_schema=INTENT_OUTPUT_SCHEMA,
        schema_name="intent-classification",
        span_name="intent-classification",
        metadata=metadata,
        tags=tags,
    )


def is_lead(
    text: str,
    niche: NicheWithConfig,
    sender_id: int | None = None,
    reply_text: str | None = None,
    reply_sender_id: int | None = None,
) -> IsLeadResult | None:
    if not reply_text:
        reply_author_relation = "reply отсутствует"
    elif sender_id is None or reply_sender_id is None:
        reply_author_relation = "неизвестно"
    elif sender_id == reply_sender_id:
        reply_author_relation = "тот же автор"
    else:
        reply_author_relation = "другой автор"

    memory_examples = (
        build_memory_examples(text=text, niche_id=niche["id"])
        if NICHE_EXAMPLES_ENABLED
        else None
    )

    niche_prompt = build_niche_prompt(
        text=text,
        niche=niche,
        reply_text=reply_text,
        reply_author_relation=reply_author_relation,
        memory_examples=memory_examples,
    )

    intent_prompt = build_intent_prompt(
        text=text,
        reply_text=reply_text,
        reply_author_relation=reply_author_relation,
    )

    niche_metadata, niche_tags = build_tracing_context(niche, NICHE_PROMPT_VERSION)
    intent_metadata, intent_tags = build_tracing_context(niche, INTENT_PROMPT_VERSION)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        niche_future = executor.submit(
            _call_niche_model, niche_prompt, niche_metadata, niche_tags
        )
        intent_future = executor.submit(
            _call_intent_model, intent_prompt, intent_metadata, intent_tags
        )

        niche_data = niche_future.result()
        intent_data = intent_future.result()

    if not niche_data or not intent_data:
        print("❌ is_lead: call_model returned None", flush=True)
        print(f"TEXT: {text}", flush=True)
        print(f"NICHE: {niche.get('name')}", flush=True)

        return None

    niche_match = niche_data.get("niche_match")
    intent_match = intent_data.get("intent_match")

    if niche_match not in MATCH_VALUES or intent_match not in MATCH_VALUES:
        ai_errors.labels(reason="invalid_match").inc()

        print(
            f"❌ Invalid match values: niche={niche_match} intent={intent_match}",
            flush=True,
        )

        return None

    verdict = combine_verdict(niche_match, intent_match)

    description = " ".join(
        part
        for part in (
            niche_data.get("description"),
            intent_data.get("description"),
        )
        if part
    )

    return IsLeadResult(
        lead=verdict != "not_lead",
        verdict=verdict,
        niche_match=niche_match,
        intent_match=intent_match,
        description=description,
        reply_author_relation=reply_author_relation,
        raw_response={"niche": niche_data, "intent": intent_data},
        prompt=f"{niche_prompt}\n\n---\n\n{intent_prompt}",
        niche_prompt_version=NICHE_PROMPT_VERSION,
        intent_prompt_version=INTENT_PROMPT_VERSION,
    )
