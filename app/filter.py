import concurrent.futures
from typing import Any, cast

from app.metrics import ai_errors, extraction_empty_total, thinking_retry_total
from app.model_client import (
    EXTRACTION_OUTPUT_SCHEMA,
    INTENT_OUTPUT_SCHEMA,
    NICHE_OUTPUT_SCHEMA,
    call_model,
)
from app.settings import (
    THINKING_MAX_TOKENS,
    THINKING_RETRY_ENABLED,
    THINKING_TIMEOUT_SECONDS,
)
from app.types import IsLeadResult, NicheWithConfig

EXTRACTION_PROMPT_VERSION = "extraction_v1"
NICHE_PROMPT_VERSION = "niche_v2"
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


EXTRACTION_STATIC_RULES = """
РОЛЬ:

Ты помощник, который выделяет из сообщения Telegram-чата конкретные
темы, объекты, процессы или услуги, если они упомянуты.


ЗАДАЧА:

Проанализируй сообщение CURRENT_USER и, если передано, сообщение
REPLY_USER. Извлеки список конкретных тем, объектов, процессов
или услуг, упомянутых в этих сообщениях — дословно или близким
пересказом.

Не оценивай, к какой сфере деятельности или компании относится
сообщение — просто перечисли, что конкретно упомянуто.


ОБОЗНАЧЕНИЯ ПОЛЬЗОВАТЕЛЕЙ:

CURRENT_USER — автор текущего сообщения.
REPLY_USER — автор сообщения, на которое отвечает CURRENT_USER.
REPLY_USER может быть тем же человеком или другим человеком.

Информация о связи между CURRENT_USER и REPLY_USER является достоверной.
Не пытайся определять авторство самостоятельно по тексту.

Если авторство REPLY_USER неизвестно, считай его другим человеком.


ПРАВИЛА:

- перечисляй только то, что явно названо в сообщениях — не додумывай
  и не обобщай смысл сообщения в тему, которой там нет;
- если CURRENT_USER и REPLY_USER — один и тот же человек, сообщение
  REPLY_USER может дополнять или продолжать тему CURRENT_USER;
- если REPLY_USER — другой человек, используй его сообщение только
  для понимания темы разговора, не приписывай его тему CURRENT_USER,
  если она не подтверждена в сообщении CURRENT_USER;
- каждая тема — короткая фраза (2-6 слов), а не пересказ всего
  сообщения;
- если сообщение не содержит ни одной конкретной темы, объекта,
  процесса или услуги — верни пустой список;
- не включай в список общие слова без конкретики (например,
  "проблема", "вопрос", "кабинет" сами по себе, если не сказано,
  какой именно кабинет или в чём проблема).


ФОРМАТ ОТВЕТА:

Верни только валидный JSON без markdown и пояснений:

{
  "topics": ["тема 1", "тема 2"]
}

Требования:

- topics — список строк, каждая строка — короткая конкретная тема;
- пустой список [], если конкретной темы нет;
- не добавляй текст до или после JSON.
""".strip()


NICHE_STATIC_RULES = """
РОЛЬ:

Ты сотрудник компании, который проверяет, соответствует ли список
тем услугам компании.


ЗАДАЧА:

Тебе передан список конкретных тем, объектов, процессов или услуг,
упомянутых в сообщении Telegram-чата. Сам текст сообщения тебе
не передаётся — только список тем.

Список может быть пустым (обрабатывается отдельно, до тебя
не доходит).

Название компании, описание ниши и ключевые слова не означают,
что список тем связан с этой нишей.

Определи одну категорию: niche_match.


NICHE_MATCH:

niche_match показывает, соответствует ли хотя бы одна тема из списка
услугам текущей ниши.

Категории:

да — хотя бы одна тема из списка напрямую соответствует конкретной
услуге, процессу или объекту из описания ниши.

спорно — есть тематическая перекличка (смежная область, похожий
процесс, общее слово), но точного соответствия конкретной услуге
ниши среди тем нет.

нет — ни одна тема из списка не соответствует услугам ниши, даже
отдалённо.

Правила:

- описание ниши используется только для сравнения и не является
  источником тем;
- ключевые слова являются только тематическими подсказками;
- сравнивай темы из списка с описанием услуг буквально — тема должна
  называть тот же объект, процесс или услугу, а не просто относиться
  к смежной или похожей области;
- совпадение с нишей должно опираться на отличительные термины ниши
  (конкретные названия систем и процессов из описания услуг), а не
  на обычные слова, которые могут описывать любую систему (например,
  "кабинет", "остатки", "склад", "коды", "отчёт", "вывод",
  "автоматизация" сами по себе, без более конкретной темы рядом);
- такое общее слово само по себе не даёт "да", максимум "спорно";
  если по остальным темам ясно, что речь о другой системе — "нет";
- если ниша упомянута только как один из нескольких несвязанных
  пунктов в общем списке разнородных тем, а не как основная тема —
  максимум "спорно";
- нельзя додумывать соответствие, которого нет явно среди
  переданных тем;
- если ни одна тема не имеет отношения к нише даже по касательной —
  "нет".


ФОРМАТ ОТВЕТА:

Верни только валидный JSON без markdown и пояснений:

{
  "niche_match": "да",
  "description": "краткое объяснение на русском языке"
}

Требования:

- niche_match — одно из значений: "да", "нет", "спорно";
- description — одно короткое предложение на русском языке,
  объясняющее, какая тема из списка (если есть) соответствует
  услугам ниши;
- не добавляй текст до или после JSON;
- description не может называть конкретную систему, кабинет
  или процесс из описания ниши, если её нет среди переданных тем.
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
- CURRENT_USER предлагает лично разобраться, проверить или ответить
  по ситуации REPLY_USER (например, «напиши в личку, посмотрю»,
  «скину ответ позже») — это помощь REPLY_USER, а не собственная
  потребность, даже если формулировка звучит как готовность помочь;
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
  может получить "да", только если из сообщения понятно, что нужно
  решение (вопрос, просьба, ожидание помощи); простая констатация
  факта или смирение с ситуацией без запроса — максимум "спорно";
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


def build_extraction_prompt(
    text: str,
    reply_text: str | None = None,
    reply_author_relation: str | None = None,
) -> str:
    reply_block = build_reply_block(reply_text, reply_author_relation)

    return f"""{EXTRACTION_STATIC_RULES}


СООБЩЕНИЕ REPLY_USER:

{reply_block}


СООБЩЕНИЕ CURRENT_USER:

{text}


ОТВЕТ:
"""


def build_niche_prompt(
    topics: list[str],
    niche: NicheWithConfig,
) -> str:
    company_name = niche.get("company_name") or "Не указана"
    niche_name = niche.get("name") or "Не указана"
    about = niche.get("about") or "Не указано"
    keywords = format_list(niche.get("keywords") or [])
    blacklist = format_list(niche.get("blacklist") or [])
    topics_block = format_list(topics)

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


СПИСОК ТЕМ ИЗ СООБЩЕНИЯ:

{topics_block}


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


def _call_extraction_model(
    prompt: str,
    metadata: dict[str, str],
    tags: list[str],
) -> dict[str, Any] | None:
    return call_model(
        prompt,
        output_schema=EXTRACTION_OUTPUT_SCHEMA,
        schema_name="topic-extraction",
        span_name="topic-extraction",
        metadata=metadata,
        tags=tags,
    )


def _call_niche_model(
    prompt: str,
    metadata: dict[str, str],
    tags: list[str],
    enable_thinking: bool = False,
    max_tokens: int = 256,
    timeout: int | None = None,
) -> dict[str, Any] | None:
    return call_model(
        prompt,
        output_schema=NICHE_OUTPUT_SCHEMA,
        schema_name="niche-classification",
        span_name="niche-classification",
        metadata=metadata,
        tags=tags,
        enable_thinking=enable_thinking,
        max_tokens=max_tokens,
        timeout=timeout,
    )


def _call_intent_model(
    prompt: str,
    metadata: dict[str, str],
    tags: list[str],
    enable_thinking: bool = False,
    max_tokens: int = 256,
    timeout: int | None = None,
) -> dict[str, Any] | None:
    return call_model(
        prompt,
        output_schema=INTENT_OUTPUT_SCHEMA,
        schema_name="intent-classification",
        span_name="intent-classification",
        metadata=metadata,
        tags=tags,
        enable_thinking=enable_thinking,
        max_tokens=max_tokens,
        timeout=timeout,
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

    extraction_prompt = build_extraction_prompt(
        text=text,
        reply_text=reply_text,
        reply_author_relation=reply_author_relation,
    )

    intent_prompt = build_intent_prompt(
        text=text,
        reply_text=reply_text,
        reply_author_relation=reply_author_relation,
    )

    extraction_metadata, extraction_tags = build_tracing_context(
        niche, EXTRACTION_PROMPT_VERSION
    )
    intent_metadata, intent_tags = build_tracing_context(niche, INTENT_PROMPT_VERSION)

    # Волна 1: извлечение тем (niche-agnostic) и intent — независимы
    # друг от друга, летят параллельно.
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        extraction_future = executor.submit(
            _call_extraction_model, extraction_prompt, extraction_metadata, extraction_tags
        )
        intent_future = executor.submit(
            _call_intent_model, intent_prompt, intent_metadata, intent_tags
        )

        extraction_data = extraction_future.result()
        intent_data = intent_future.result()

    if not extraction_data or not intent_data:
        print("❌ is_lead: call_model returned None", flush=True)
        print(f"TEXT: {text}", flush=True)
        print(f"NICHE: {niche.get('name')}", flush=True)

        return None

    raw_topics = extraction_data.get("topics")
    intent_match = intent_data.get("intent_match")

    valid_topics = False

    if isinstance(raw_topics, list):
        candidate_topics = cast(list[Any], raw_topics)
        valid_topics = all(isinstance(item, str) for item in candidate_topics)

    if not valid_topics:
        ai_errors.labels(reason="invalid_extraction").inc()

        print(f"❌ Invalid extraction topics: {raw_topics!r}", flush=True)

        return None

    topics = cast(list[str], raw_topics)

    if intent_match not in MATCH_VALUES:
        ai_errors.labels(reason="invalid_match").inc()

        print(f"❌ Invalid intent_match: {intent_match}", flush=True)

        return None

    # Волна 2: сопоставление с нишей — только если извлечены темы.
    # Пустой список тем -> "нет" без обращения к модели ниши вообще.
    niche_prompt: str | None = None
    niche_metadata, niche_tags = build_tracing_context(niche, NICHE_PROMPT_VERSION)

    if not topics:
        extraction_empty_total.labels(
            company_id=str(niche["company_id"]),
            niche_id=str(niche["id"]),
        ).inc()

        niche_match = "нет"
        niche_data: dict[str, Any] = {
            "niche_match": "нет",
            "description": "Конкретная тема в сообщении не выявлена.",
        }
    else:
        niche_prompt = build_niche_prompt(topics=topics, niche=niche)

        niche_data_result = _call_niche_model(niche_prompt, niche_metadata, niche_tags)

        if not niche_data_result:
            print("❌ is_lead: call_model returned None", flush=True)
            print(f"TEXT: {text}", flush=True)
            print(f"NICHE: {niche.get('name')}", flush=True)

            return None

        niche_match = niche_data_result.get("niche_match")

        if niche_match not in MATCH_VALUES:
            ai_errors.labels(reason="invalid_match").inc()

            print(f"❌ Invalid niche_match: {niche_match}", flush=True)

            return None

        niche_data = niche_data_result

    if THINKING_RETRY_ENABLED:
        retry_niche = niche_prompt is not None and niche_match != "нет"
        retry_intent = intent_match != "нет"

        if retry_niche or retry_intent:
            if retry_niche:
                thinking_retry_total.labels(axis="niche").inc()

            if retry_intent:
                thinking_retry_total.labels(axis="intent").inc()

            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                niche_retry_future = (
                    executor.submit(
                        _call_niche_model,
                        niche_prompt,
                        niche_metadata,
                        niche_tags,
                        enable_thinking=True,
                        max_tokens=THINKING_MAX_TOKENS,
                        timeout=THINKING_TIMEOUT_SECONDS,
                    )
                    if retry_niche and niche_prompt is not None
                    else None
                )
                intent_retry_future = (
                    executor.submit(
                        _call_intent_model,
                        intent_prompt,
                        intent_metadata,
                        intent_tags,
                        enable_thinking=True,
                        max_tokens=THINKING_MAX_TOKENS,
                        timeout=THINKING_TIMEOUT_SECONDS,
                    )
                    if retry_intent
                    else None
                )

                if niche_retry_future is not None:
                    retried_niche_data = niche_retry_future.result()

                    if (
                        retried_niche_data
                        and retried_niche_data.get("niche_match") in MATCH_VALUES
                    ):
                        niche_data = retried_niche_data
                        niche_match = retried_niche_data["niche_match"]

                if intent_retry_future is not None:
                    retried_intent_data = intent_retry_future.result()

                    if (
                        retried_intent_data
                        and retried_intent_data.get("intent_match") in MATCH_VALUES
                    ):
                        intent_data = retried_intent_data
                        intent_match = retried_intent_data["intent_match"]

    verdict = combine_verdict(niche_match, intent_match)

    description = " ".join(
        part
        for part in (
            niche_data.get("description"),
            intent_data.get("description"),
        )
        if part
    )

    prompt_parts = [extraction_prompt]

    if niche_prompt is not None:
        prompt_parts.append(niche_prompt)

    prompt_parts.append(intent_prompt)

    return IsLeadResult(
        lead=verdict != "not_lead",
        verdict=verdict,
        niche_match=niche_match,
        intent_match=intent_match,
        description=description,
        reply_author_relation=reply_author_relation,
        raw_response={"extraction": extraction_data, "niche": niche_data, "intent": intent_data},
        prompt="\n\n---\n\n".join(prompt_parts),
        niche_prompt_version=NICHE_PROMPT_VERSION,
        intent_prompt_version=INTENT_PROMPT_VERSION,
    )
