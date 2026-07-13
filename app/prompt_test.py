import json
import os
import time
from datetime import datetime, timezone

from app.bootstrap import bootstrap_app
from app.db.niches import get_active_niches
from app.filter import is_lead


CHZ = "Маркировка Честный знак"
WEB = "Разработка сайтов"


def tc(
    case_id: str,
    text: str,
    *,
    chz: bool = False,
    web: bool = False,
    reply_text: str | None = None,
):
    return {
        "id": case_id,
        "text": text,
        "reply_text": reply_text,
        "expected": {
            CHZ: chz,
            WEB: web,
        },
    }


TEST_CASES = [
    # Общие сообщения без указанной темы
    tc(
        "generic_help_emoji",
        "🙏 пожалуйста, очень поможете!",
    ),
    tc(
        "generic_paid_help",
        "нужна помощь, кто готов — маякните, в конце по 10 000 даю",
    ),
    tc(
        "generic_task_paid",
        "дело на пару часов — оплата 12 000 р.",
    ),
    tc(
        "generic_one_task",
        "народ, кто сейчас готов помочь по одному делу? займет минимум времени",
    ),
    tc(
        "generic_urgent",
        "срочно нужен человек, пишите в личку",
    ),
    tc(
        "generic_question",
        "кто-нибудь сталкивался с такой проблемой?",
    ),
    tc(
        "generic_thanks",
        "спасибо всем, уже разобрался",
    ),

    # Честный знак: конкретные задачи и вопросы
    tc(
        "chz_error",
        "у меня ошибка в ЧЗ, что делать?",
        chz=True,
    ),
    tc(
        "chz_codes_error",
        "не могу выпустить коды маркировки, постоянно выходит ошибка",
        chz=True,
    ),
    tc(
        "chz_registration",
        "как зарегистрировать ИП в Честном знаке?",
        chz=True,
    ),
    tc(
        "chz_gs1",
        "подскажите, как пройти регистрацию в GS1",
        chz=True,
    ),
    tc(
        "chz_tnved",
        "нужно проверить ТН ВЭД и понять, попадает ли товар под маркировку",
        chz=True,
    ),
    tc(
        "chz_product_required",
        "как понять, нужно ли маркировать мой товар?",
        chz=True,
    ),
    tc(
        "chz_cosmetics",
        "начинаем продавать косметику, что нужно сделать по маркировке?",
        chz=True,
    ),
    tc(
        "chz_leftovers",
        "как правильно начать маркировку остатков в рознице?",
        chz=True,
    ),
    tc(
        "chz_cabinet",
        "не получается настроить личный кабинет Честного знака",
        chz=True,
    ),
    tc(
        "chz_print_codes",
        "как подготовить и распечатать коды DataMatrix?",
        chz=True,
    ),
    tc(
        "chz_upd",
        "как передать УПД с кодами маркировки?",
        chz=True,
    ),
    tc(
        "chz_marketplace",
        "как передать коды маркировки на Озон?",
        chz=True,
    ),
    tc(
        "chz_training",
        "кто может обучить работе в Честном знаке?",
        chz=True,
    ),
    tc(
        "chz_inventory",
        "нужно провести инвентаризацию в Честном знаке",
        chz=True,
    ),
    tc(
        "chz_under_key",
        "помогите срочно с ЧЗ под ключ",
        chz=True,
    ),
    tc(
        "chz_kiz",
        "кто делает КИЗ для ЧЗ? нужна помощь",
        chz=True,
    ),
    tc(
        "chz_mercury",
        "нужно зарегистрироваться в Меркурии, кто подскажет порядок?",
        chz=True,
    ),

    # Честный знак: нецелевые сообщения
    tc(
        "chz_sell_codes",
        "продам готовые коды маркировки недорого",
    ),
    tc(
        "chz_buy_codes",
        "куплю готовые коды для обуви без документов",
    ),
    tc(
        "chz_1c_integration",
        "кто настроит интеграцию Честного знака с 1С?",
    ),
    tc(
        "chz_service_offer",
        "занимаюсь маркировкой под ключ, пишите в личку",
    ),
    tc(
        "chz_vacancy",
        "требуется оператор Честного знака в штат",
    ),
    tc(
        "chz_news",
        "с сентября вступают новые правила маркировки одежды",
    ),
    tc(
        "chz_definition",
        "что такое Честный знак?",
        chz=True,
    ),
    tc(
        "chz_success",
        "мы наконец-то сами выпустили все коды в ЧЗ",
    ),
    tc(
        "chz_printer",
        "какой принтер лучше купить для этикеток?",
    ),

    # Разработка сайтов: целевые задачи
    tc(
        "web_site_specialist",
        "сайты делает кто-нибудь? нужен специалист, пишите в лс",
        web=True,
    ),
    tc(
        "web_landing",
        "нужен лендинг для услуги, кто может сделать?",
        web=True,
    ),
    tc(
        "web_store",
        "нужно разработать интернет-магазин с оплатой",
        web=True,
    ),
    tc(
        "web_broken_form",
        "на сайте сломалась форма заявки, кто может исправить?",
        web=True,
    ),
    tc(
        "web_redesign",
        "нужно обновить дизайн старого сайта",
        web=True,
    ),
    tc(
        "web_speed",
        "сайт очень медленно загружается, нужна помощь",
        web=True,
    ),

    # Разработка сайтов: нецелевые сообщения
    tc(
        "web_platform_question",
        "подскажите, на чем лучше сделать сайт?",
        web=True,
    ),
    tc(
        "web_service_offer",
        "делаю сайты и лендинги недорого, обращайтесь",
    ),
    tc(
        "web_vacancy",
        "ищем frontend-разработчика в штат",
    ),
    tc(
        "web_discussion",
        "у конкурентов недавно появился новый сайт",
    ),

    # Reply-контекст
    tc(
        "reply_chz_paid",
        "кто может помочь платно?",
        reply_text="у меня ошибка в ЧЗ, не могу выпустить коды маркировки",
        chz=True,
    ),
    tc(
        "reply_chz_price",
        "а сколько будет стоить?",
        reply_text="нужно зарегистрировать компанию в Честном знаке",
        chz=True,
    ),
    tc(
        "reply_chz_question",
        "подскажите, как правильно сделать?",
        reply_text="надо передать коды маркировки на Озон",
        chz=True,
    ),
    tc(
        "reply_chz_offer",
        "могу вам с этим помочь, напишите мне",
        reply_text="не получается выпустить коды в ЧЗ",
    ),
    tc(
        "reply_web_paid",
        "кто может помочь платно?",
        reply_text="сломалась форма заявки на сайте, заявки не приходят",
        web=True,
    ),
    tc(
        "reply_web_price",
        "сколько будет стоить такая работа?",
        reply_text="нужно сделать новый лендинг для компании",
        web=True,
    ),
]


def find_expected(case: dict, niche: dict) -> bool:
    expected = case.get("expected") or {}

    niche_name = niche.get("name") or ""
    company_name = niche.get("company_name") or ""

    haystack = f"{company_name} {niche_name}".lower()

    for key, value in expected.items():
        if key.lower() in haystack:
            return bool(value)

    return False


def print_header():
    print("")
    print("=" * 100)
    print("PROMPT TEST")
    print("=" * 100)
    print(f"created_at: {datetime.now(timezone.utc).isoformat()}")
    print(f"MODEL_NAME: {os.getenv('MODEL_NAME')}")
    print(f"MIN_NICHE_SCORE: {os.getenv('MIN_NICHE_SCORE')}")
    print(f"MIN_INTENT_SCORE: {os.getenv('MIN_INTENT_SCORE')}")
    print(f"MEMORY_MAX_DISTANCE: {os.getenv('MEMORY_MAX_DISTANCE')}")
    print("=" * 100)


def print_case_result(case, niche, result, expected, elapsed):
    niche_title = f"{niche.get('company_name')} / {niche.get('name')}"

    lead = result.get("lead") if result else None
    niche_score = result.get("niche_score") if result else None
    intent_score = result.get("intent_score") if result else None
    description = result.get("description") if result else "EMPTY RESULT"
    prompt_version = result.get("prompt_version") if result else None

    ok = lead == expected
    status = "OK" if ok else "FAIL"

    print("")
    print("-" * 100)
    print(f"[{status}] {case['id']} → {niche_title}")
    print(f"text: {case['text']}")

    if case.get("reply_text"):
        print(f"reply: {case['reply_text']}")

    print(f"expected: {expected}")
    print(f"actual:   {lead}")
    print(f"niche:    {niche_score}")
    print(f"intent:   {intent_score}")
    print(f"reason:   {description}")
    print(f"prompt:   {prompt_version}")
    print(f"time:     {round(elapsed, 2)}s")


def run_test():
    bootstrap_app()

    niches = get_active_niches()

    print_header()

    print("ACTIVE NICHES:")
    for niche in niches:
        print(
            f"- {niche.get('company_name')} / "
            f"{niche.get('name')} id={niche.get('id')}"
        )

    checked = 0
    passed = 0
    failed = 0
    true_positive = 0
    true_negative = 0
    false_positive = 0
    false_negative = 0

    results_for_json = []

    for case in TEST_CASES:
        for niche in niches:
            expected = find_expected(case, niche)

            started_at = time.time()

            try:
                result = is_lead(
                    text=case["text"],
                    tg_chat_id=0,
                    tg_message_id=0,
                    niche=niche,
                    reply_tg_message_id=None,
                    reply_text=case.get("reply_text"),
                )
            except Exception as e:
                result = {
                    "lead": None,
                    "niche_score": None,
                    "intent_score": None,
                    "description": f"ERROR: {type(e).__name__}: {e}",
                    "prompt_version": None,
                }

            elapsed = time.time() - started_at

            print_case_result(
                case=case,
                niche=niche,
                result=result,
                expected=expected,
                elapsed=elapsed,
            )

            lead = result.get("lead") if result else None
            ok = lead == expected

            checked += 1

            if ok:
                passed += 1
            else:
                failed += 1

            if expected is True and lead is True:
                true_positive += 1
            elif expected is False and lead is False:
                true_negative += 1
            elif expected is False and lead is True:
                false_positive += 1
            elif expected is True and lead is False:
                false_negative += 1

            results_for_json.append(
                {
                    "case_id": case["id"],
                    "text": case["text"],
                    "reply_text": case.get("reply_text"),
                    "niche": niche.get("name"),
                    "company": niche.get("company_name"),
                    "expected": expected,
                    "actual": lead,
                    "niche_score": (
                        result.get("niche_score") if result else None
                    ),
                    "intent_score": (
                        result.get("intent_score") if result else None
                    ),
                    "description": (
                        result.get("description") if result else None
                    ),
                    "prompt_version": (
                        result.get("prompt_version") if result else None
                    ),
                    "ok": ok,
                    "time_seconds": round(elapsed, 2),
                }
            )

    precision = (
        true_positive / (true_positive + false_positive)
        if true_positive + false_positive
        else None
    )
    recall = (
        true_positive / (true_positive + false_negative)
        if true_positive + false_negative
        else None
    )
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None
        and recall is not None
        and precision + recall
        else None
    )

    summary = {
        "checked": checked,
        "passed": passed,
        "failed": failed,
        "accuracy": round(passed / checked, 3) if checked else None,
        "true_positive": true_positive,
        "true_negative": true_negative,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "precision": round(precision, 3) if precision is not None else None,
        "recall": round(recall, 3) if recall is not None else None,
        "f1": round(f1, 3) if f1 is not None else None,
    }

    print("")
    print("=" * 100)
    print("SUMMARY")
    print("=" * 100)
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    print("")
    print("=" * 100)
    print("JSON_RESULT")
    print("=" * 100)
    print(
        json.dumps(
            {
                "summary": summary,
                "results": results_for_json,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    run_test()