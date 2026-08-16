from typing import Any

from app.metrics import ai_errors
from app.model_client import call_model
from app.retrieval import find_similar_messages
from app.settings import MIN_INTENT_SCORE, MIN_NICHE_SCORE
from app.types import IsLeadResult, NicheId, NicheWithConfig

PROMPT_VERSION = "classifier_v13"


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


STATIC_RULES = """
РОЛЬ:

Ты сотрудник компании, который ищет потенциальных клиентов
в общем потоке сообщений из разных Telegram-чатов.


ЗАДАЧА:

Проанализируй одно сообщение CURRENT_USER.

Сообщение может относиться к любой теме.
Название компании, описание ниши и ключевые слова не означают,
что сообщение связано с этой нишей.

Независимо оцени два показателя:

1. niche_score
2. intent_score


ОБОЗНАЧЕНИЯ ПОЛЬЗОВАТЕЛЕЙ:

CURRENT_USER — автор текущего сообщения.
Только CURRENT_USER оценивается как потенциальный лид.

REPLY_USER — автор сообщения, на которое отвечает CURRENT_USER.
REPLY_USER может быть тем же человеком или другим человеком.

Информация о связи между CURRENT_USER и REPLY_USER является достоверной.
Не пытайся определять авторство самостоятельно по тексту.


ТОЧНОСТЬ ШКАЛ:

Для итогового решения важно только, попадает ли оценка в диапазон 75-100
или нет. Как только это понятно, не трать рассуждения на выбор точного
числа между соседними диапазонами шкалы (например, 50-74 и 75-89) —
бери любое значение из уже определившейся стороны шкалы и переходи дальше.


NICHE_SCORE:

niche_score показывает, насколько тема или задача сообщения CURRENT_USER
относится к услугам текущей ниши.

Для определения темы используй сообщение CURRENT_USER
и сообщение REPLY_USER, если оно передано.

Шкала:

0-20 — другая тема или задача не указана.
21-49 — возможна слабая связь, которую приходится додумывать.
50-74 — сообщение тематически близко, но задача описана неясно.
75-89 — тема или задача явно относится к текущей нише.
90-100 — задача напрямую соответствует конкретным услугам текущей ниши.

Правила:

- описание ниши используется только для сравнения и не является
  контекстом сообщения;
- ключевые слова являются только тематическими подсказками;
- нельзя переносить информацию из описания ниши в сообщение CURRENT_USER;
- нельзя додумывать отсутствующую тему или задачу;
- просьба о помощи не повышает niche_score без указания темы;
- упоминание оплаты не повышает niche_score;
- поиск исполнителя не повышает niche_score, если задача неизвестна;
- сообщение, подходящее к любой профессии или услуге, должно получить 0-30;
- запрос по другой нише должен получить низкий niche_score;
- направление из списка исключений должно получить низкий niche_score;
- niche_score 75 и выше допустим только тогда, когда сообщение CURRENT_USER
  содержит конкретную тему, объект, процесс или проблему,
  которые можно напрямую сопоставить с услугами ниши;
- если CURRENT_USER и REPLY_USER — один и тот же человек,
  сообщение REPLY_USER может восстановить пропущенную часть
  собственной задачи CURRENT_USER;
- если REPLY_USER — другой человек, его сообщение можно использовать
  только для уточнения смысла уже имеющихся слов и ссылок
  в сообщении CURRENT_USER;
- тема или задача, присутствующая только в сообщении REPLY_USER,
  не позволяет выставить CURRENT_USER niche_score выше 49;
- если связь с нишей строится только на общих словах, тематических подсказках,
  предполагаемом контексте чата или описании услуг, niche_score должен быть
  не выше 49;
- если сообщение CURRENT_USER можно полностью понять без обращения
  к услугам текущей ниши, нельзя додумывать связь с ней.


INTENT_SCORE:

intent_score показывает, насколько CURRENT_USER сам нуждается
в помощи, консультации, обучении, сопровождении или выполнении задачи.

Оценивай намерение только CURRENT_USER.

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

Высокий intent_score допустим только тогда, когда CURRENT_USER
выражает собственную нерешённую потребность.

Наличие темы ниши, вопроса или просьбы в сообщении REPLY_USER
не является доказательством потребности CURRENT_USER.


СВЯЗЬ CURRENT_USER И REPLY_USER:

Если CURRENT_USER и REPLY_USER — один и тот же человек:

- сообщение REPLY_USER может содержать предыдущую часть
  собственной задачи CURRENT_USER;
- оценивай оба сообщения как продолжение одной мысли;
- короткое уточнение, вопрос о стоимости, порядке действий, сроках,
  последствиях или инструкции может получить высокий intent_score;
- благодарность или подтверждение не снижают intent_score,
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
  является частью помощи REPLY_USER
  и должен получить intent_score не выше 20;
- реакция, комментарий или продолжение обсуждения ситуации REPLY_USER
  без попытки помочь и без собственной задачи CURRENT_USER
  должны получить intent_score от 21 до 49;
- если нельзя уверенно определить, относится ли вопрос
  к собственной задаче CURRENT_USER или к ситуации REPLY_USER,
  intent_score должен быть не выше 49;
- сообщение о том, что CURRENT_USER связался с другим участником,
  продолжил общение в другом месте или уже совершил некоторое действие,
  само по себе не является запросом услуги;
- краткое указание, что следует сделать, является решением или советом,
  а не собственной задачей CURRENT_USER;
- ответ, совет, инструкция, готовое решение, диагностика или разъяснение
  должны получить intent_score не выше 20;
- высокий intent_score возможен только тогда, когда CURRENT_USER
  явно описывает собственную аналогичную задачу, просит решение для себя,
  ищет исполнителя или запрашивает консультацию для своего случая.

Если авторство REPLY_USER неизвестно (не подтверждено, что это тот же
или другой человек), применяй правила как для другого человека:
без подтверждения нельзя считать REPLY_USER тем же человеком.

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

Такие сообщения должны получить intent_score не выше 20,
даже если сообщение REPLY_USER содержит явную проблему
потенциального клиента.

Шкала:

0-20 — CURRENT_USER не ищет помощь: отвечает, консультирует,
диагностирует, даёт инструкцию, задаёт диагностический
или уточняющий вопрос для помощи REPLY_USER,
предлагает собственные услуги, сообщает информацию
или описывает уже совершённое действие.

21-49 — CURRENT_USER реагирует, комментирует
или продолжает обсуждение чужой ситуации,
выражает неясный интерес либо возможную,
но не подтверждённую собственную задачу.

50-74 — CURRENT_USER явно описывает собственную ситуацию или задачу,
но потребность в помощи, консультации или выполнении работы
выражена неясно.

75-89 — CURRENT_USER явно описывает собственную нерешённую задачу,
задаёт вопрос по своему случаю или просит совет,
но прямо не ищет исполнителя и не запрашивает выполнение услуги.

90-100 — CURRENT_USER прямо ищет специалиста или исполнителя,
просит оказать услугу, запрашивает стоимость, сроки или условия
выполнения работы для себя.

Правила:

- конкретный вопрос по теме ниши может получить высокий intent_score,
  только если относится к собственной ситуации CURRENT_USER;
- вопрос о выборе способа, порядке действий, правилах, сроках,
  последствиях, инструкции или значении термина
  может быть запросом на консультацию;
- уточняющий вопрос может получить высокий intent_score,
  только если относится к собственной задаче CURRENT_USER;
- CURRENT_USER необязательно прямо искать платную услугу или исполнителя;
- описание ошибки или собственной проблемы CURRENT_USER
  может получить высокий intent_score;
- вопрос о стоимости является признаком явного намерения,
  если стоимость интересует CURRENT_USER;
- предложение собственных услуг не является потребностью CURRENT_USER;
- поиск сотрудника в штат не является запросом услуги;
- новости и объявления без вопроса или нерешённой задачи
  должны получить низкий intent_score;
- наличие темы ниши само по себе не повышает intent_score;
- нельзя считать любое сообщение с вопросительным знаком
  запросом на услугу;
- нельзя считать любой вопрос собственной потребностью CURRENT_USER.


ПРАВИЛА ИСПОЛЬЗОВАНИЯ ПРИМЕРОВ:

Ниже будет передан блок примеров с оценкой человека.

- true означает, что оператор положительно оценил конкретное сообщение;
- false означает, что оператор отрицательно оценил конкретное сообщение;
- причины оценки отдельно не классифицировались и неизвестны;
- не пытайся выводить из true обязательное наличие явной потребности,
  готовности купить или конкретного типа запроса;
- используй примеры только как ориентиры для похожих случаев;
- не копируй оценку автоматически по совпадению отдельных слов;
- не переноси факты или намерения из примеров в сообщение CURRENT_USER;
- niche_score и intent_score для CURRENT_USER выставляй самостоятельно.


ФОРМАТ ОТВЕТА:

Верни только валидный JSON без markdown и пояснений:

{
  "niche_score": 0,
  "intent_score": 0,
  "description": "краткое объяснение оценок"
}

Требования:

- niche_score — целое число от 0 до 100;
- intent_score — целое число от 0 до 100;
- description — одно короткое предложение на русском языке;
- description объясняет связь с нишей и коммуникативную роль CURRENT_USER;
- если CURRENT_USER отвечает, консультирует или диагностирует
  ситуацию REPLY_USER, description должно прямо это отражать;
- не возвращай поле lead;
- не добавляй текст до или после JSON;
- description не должно утверждать наличие темы или задачи,
  которых нет в сообщении CURRENT_USER или сообщении REPLY_USER;
- description не должно приписывать CURRENT_USER
  проблему или потребность REPLY_USER.
""".strip()


def build_prompt(
    text: str,
    niche: NicheWithConfig,
    memory_examples: str,
    reply_text: str | None = None,
    reply_author_relation: str | None = None,
) -> str:
    company_name = niche.get("company_name") or "Не указана"
    niche_name = niche.get("name") or "Не указана"
    about = niche.get("about") or "Не указано"
    keywords = format_list(niche.get("keywords") or [])
    blacklist = format_list(niche.get("blacklist") or [])
    # есть в админке, надо добавить в промт
    # extra_rules = format_list(niche.get("blacklist") or [])

    if reply_text:
        reply_block = f"""
    Связь CURRENT_USER и REPLY_USER:
    {reply_author_relation}

    Сообщение REPLY_USER:
    {reply_text}
        """.strip()
    else:
        reply_block = "Сообщение REPLY_USER отсутствует."

    return f"""{STATIC_RULES}


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


ПРИМЕРЫ С ОЦЕНКОЙ ЧЕЛОВЕКА:

{memory_examples}


СООБЩЕНИЕ REPLY_USER:

{reply_block}


СООБЩЕНИЕ CURRENT_USER:

{text}


ОТВЕТ:
"""


def normalize_ai_score(value: Any) -> int:
    try:
        score = int(value)
    except (TypeError, ValueError):
        return 0

    return max(0, min(score, 100))


def build_tracing_context(niche: NicheWithConfig) -> tuple[dict[str, str], list[str]]:
    company_name = str(niche.get("company_name") or "Не указана").strip() or "Не указана"
    niche_name = str(niche.get("name") or "Не указана").strip() or "Не указана"
    niche_slug = str(niche.get("slug") or "").strip()

    metadata: dict[str, str] = {
        "company_id": str(niche["company_id"]),
        "company_name": company_name,
        "niche_id": str(niche["id"]),
        "niche_name": niche_name,
        "promptversion": PROMPT_VERSION,
    }

    if niche_slug:
        metadata["niche_slug"] = niche_slug

    niche_label = f"{company_name} / {niche_name}"
    tag_value = f"niche:{niche_label}"[:200]
    tags = [tag_value]

    return metadata, tags


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

    memory_examples = ''
    # memory_examples = build_memory_examples(
    #     text=text,
    #     niche_id=niche["id"],
    # )

    tracing_metadata, tracing_tags = build_tracing_context(niche)

    prompt = build_prompt(
        text=text,
        niche=niche,
        memory_examples=memory_examples,
        reply_text=reply_text,
        reply_author_relation=reply_author_relation,
    )

    data = call_model(
        prompt,
        metadata=tracing_metadata,
        tags=tracing_tags,
    )

    if not data:
        print("❌ is_lead: call_model returned None", flush=True)
        print(f"TEXT: {text}", flush=True)
        print(f"NICHE: {niche.get('name')}", flush=True)

        return None

    raw_niche_score = data.get("niche_score")
    raw_intent_score = data.get("intent_score")

    if (
        not isinstance(raw_niche_score, int) or not isinstance(raw_intent_score, int)
    ):
        ai_errors.labels(reason="invalid_scores").inc()
        print(f"❌ Invalid niche_score: {raw_niche_score}", flush=True)

        return None

    niche_score = int(raw_niche_score)
    intent_score = int(raw_intent_score)

    final_lead = (
        niche_score >= MIN_NICHE_SCORE
        and intent_score >= MIN_INTENT_SCORE
    )

    return IsLeadResult(
        lead=final_lead,
        niche_score=niche_score,
        intent_score=intent_score,
        description=data.get("description") or "",
        reply_author_relation=reply_author_relation,
        raw_response=data,
        prompt=prompt,
        prompt_version=PROMPT_VERSION,
    )
