from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast, TypedDict

import app.filter as lead_filter
from app.types import NicheId, NicheWithConfig, CompanyId

MARKING_NICHE: NicheWithConfig = {
    "id": NicheId(1),
    "name": "Маркировка Честный знак",
    "slug": "marking",
    "company_id": CompanyId(1),
    "company_name": "Мой знак",
    "about": (
        "Помощь бизнесу с обязательной маркировкой товаров и системой "
        "«Честный знак»: регистрация, карточки товаров, заказ и нанесение "
        "кодов, ввод и вывод из оборота, маркировка остатков, УПД и ЭДО, "
        "работа с КИЗ, импорт, агрегация, исправление ошибок, консультации "
        "и сопровождение."
    ),
    "extra_instructions": None,
    "keywords": [
        "Честный знак", "маркировка", "КИЗ", "код маркировки",
        "ввод в оборот", "вывод из оборота", "маркировка остатков",
        "УПД", "ЭДО", "GTIN", "Национальный каталог",
        "ФБС", "ФБО", "импорт", "агрегация",
    ],
    "blacklist": [
        "готовые коды маркировки", "серый товар", "товар с рынка",
        "товар с Садовода", "карго", "настройка Честного знака с 1С",
        "интеграция Честного знака с 1С",
        "настройка Честного знака с МойСклад", "покупка кодов по УПД",
    ],
}

Expected = Literal["lead", "not_lead"]
Actual = Literal["lead", "not_lead", "error"]


class PromptCaseResult(TypedDict):
    name: str
    expected: Expected
    actual: Actual
    passed: bool
    niche_score: int | None
    intent_score: int | None
    description: str
    note: str


@dataclass(frozen=True)
class PromptCase:
    name: str
    text: str
    expected: Expected
    reply_text: str | None = None
    same_reply_author: bool | None = None
    note: str = ""


CASES: list[PromptCase] = [
    PromptCase(
        name="fbs_instructions",
        text=(
            "Добрый день! Подскажите инструкции по отгрузке маркированных "
            "товаров по ФБС на ВБ. КИЗ указали в сборочном задании, товар "
            "отгрузили. Какие дальше действия и нужно ли выводить КИЗ из оборота?"
        ),
        expected="lead",
    ),
    PromptCase(
        name="import_aggregation",
        text=(
            "После импорта нужно ввести в оборот 5000 единиц. Можно ли создать "
            "агрегационные коды, чтобы не сканировать каждый КМ поштучно?"
        ),
        expected="lead",
    ),
    PromptCase(
        name="marking_deadline",
        text=(
            "Подскажите, с какой даты обязательна маркировка глюкометров "
            "и тест-полосок? Они ещё во втором этапе эксперимента?"
        ),
        expected="lead",
    ),
    PromptCase(
        name="return_code_to_turnover",
        text=(
            "Товар вернули, КМ уже выбыл. Как вернуть код маркировки в оборот, "
            "если 1С пишет, что КМ не принадлежит нашему юрлицу?"
        ),
        expected="lead",
    ),
    PromptCase(
        name="recommend_upd_bot",
        text="Посоветуйте, пожалуйста, бота для передачи УПД в Честный знак.",
        expected="lead",
    ),
    PromptCase(
        name="promo_box",
        text=(
            "Нужно ли наносить коды маркировки на каждое вложение, если товар "
            "продаётся только целиком как промобокс?"
        ),
        expected="lead",
    ),
    PromptCase(
        name="reply_same_author_continuation",
        text="А если указали количество 1 вместо 200, как теперь это исправить?",
        reply_text=(
            "В отчёте о нанесении нужно указывать фактическое количество "
            "в переменной характеристике на каждый код."
        ),
        same_reply_author=True,
        expected="lead",
    ),
    PromptCase(
        name="reply_other_author_own_problem",
        text=(
            "Я уже написала в поддержку, но КИЗ ввели в оборот. "
            "Что теперь делать, пока не отправлять товар?"
        ),
        reply_text="Напишите им, они должны разобраться.",
        same_reply_author=False,
        expected="lead",
    ),
    PromptCase(
        name="reply_other_author_advice",
        text=(
            "Смотреть нужно через личный кабинет Честного знака. "
            "Поставщик должен написать в поддержку, другого способа исправить код нет."
        ),
        reply_text=(
            "Как понять, что у кода нет переменной характеристики? "
            "У меня похожая ситуация."
        ),
        same_reply_author=False,
        expected="not_lead",
    ),
    PromptCase(
        name="reply_other_author_diagnostic_question",
        text="Декларацию подписали, пошлина списалась, но запись не появилась в реестре?",
        reply_text=(
            "Подписали документ, а в Честном знаке теперь написано "
            "«не найден в реестре»."
        ),
        same_reply_author=False,
        expected="not_lead",
    ),
    PromptCase(
        name="advice_about_old_stock",
        text=(
            "Поставьте дату производства до начала маркировки и распродайте остатки. "
            "ВБ и Ozon товар без КИЗ всё равно не примут."
        ),
        reply_text="Как продать остатки без маркировки?",
        same_reply_author=False,
        expected="not_lead",
    ),
    PromptCase(
        name="marketplace_packaging_not_marking",
        text=(
            "Грузоместо — это общая коробка. QR-код клеится только на неё, "
            "а на коробках товаров остаются штрихкоды и QR-коды ВБ."
        ),
        reply_text="Куда клеить QR-код грузоместа при отгрузке на ПВЗ?",
        same_reply_author=False,
        expected="not_lead",
    ),
    PromptCase(
        name="gray_goods",
        text="Есть у кого контакты, кто делает Честный знак для серого товара?",
        expected="not_lead",
    ),
    PromptCase(
        name="one_c_integration",
        text=(
            "Кто может настроить интеграцию Честного знака с 1С, "
            "чтобы КМ автоматически передавались по УПД?"
        ),
        expected="not_lead",
    ),
    PromptCase(
        name="generic_help",
        text="Помогите, кто сможет?",
        expected="not_lead",
    ),
    PromptCase(
        name="unrelated_marketplace_question",
        text="Подскажите, почему карточка товара на Ozon уже второй день на модерации?",
        expected="not_lead",
    ),
    PromptCase(
        name="printer_recommendation",
        text=(
            "Посоветуйте надёжный и недорогой принтер для печати этикеток "
            "маркировки, у моего принтера слишком дорогая лента."
        ),
        expected="not_lead",
    ),
    PromptCase(
        name="supplier_must_mark",
        text=(
            "Все новые игрушки теперь поставщик должен передавать уже "
            "маркированными или нам нужно заказывать коды самостоятельно?"
        ),
        expected="lead",
    ),
]


def relation_ids(case: PromptCase) -> tuple[int | None, int | None]:
    if case.reply_text is None:
        return 1001, None
    if case.same_reply_author:
        return 1001, 1001
    if case.same_reply_author is False:
        return 1001, 2002
    return 1001, None


def run_case(
    case: PromptCase,
    niche: NicheWithConfig,
) -> PromptCaseResult:
    sender_id, reply_sender_id = relation_ids(case)
    result = lead_filter.is_lead(
        text=case.text,
        niche=niche,
        sender_id=sender_id,
        reply_text=case.reply_text,
        reply_sender_id=reply_sender_id,
    )

    if result is None:
        return {
            "name": case.name,
            "expected": case.expected,
            "actual": "error",
            "passed": False,
            "niche_score": None,
            "intent_score": None,
            "description": "Модель не вернула результат",
            "note": case.note,
        }

    actual: Actual = "lead" if result["lead"] else "not_lead"
    return {
        "name": case.name,
        "expected": case.expected,
        "actual": actual,
        "passed": actual == case.expected,
        "niche_score": result["niche_score"],
        "intent_score": result["intent_score"],
        "description": result["description"],
        "note": case.note,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Регрессионный прогон промпта для ниши маркировки."
    )
    parser.add_argument(
        "--niche-id",
        type=int,
        default=1,
        help="ID ниши маркировки в текущей базе.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Сохранить подробный JSON-отчёт.",
    )
    args = parser.parse_args()

    niche = cast(
        NicheWithConfig,
            cast(object, {
                **MARKING_NICHE,
                "id": NicheId(args.niche_id),
            }),
        )

    results: list[PromptCaseResult] = []

    print(
        f"\nКоличество кейсов: {len(CASES)}\n"
    )

    for index, case in enumerate(CASES, start=1):
        result = run_case(case, niche)
        results.append(result)

        marker = "✅" if result["passed"] else "❌"

        print(
            f"{marker} {index:02d}. {case.name}\n"
            f"   expected={result['expected']} "
            f"actual={result['actual']}\n"
            f"   niche={result['niche_score']} "
            f"intent={result['intent_score']}\n"
            f"   {result['description']}\n"
        )

    passed = sum(
        result["passed"]
        for result in results
    )
    failed = len(results) - passed

    print("-" * 72)
    print(
        f"Итог: {passed}/{len(results)} успешно, "
        f"ошибок: {failed}"
    )

    if args.output is not None:
        report = {
            "niche_id": args.niche_id,
            "passed": passed,
            "failed": failed,
            "total": len(results),
            "results": results,
        }

        args.output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        args.output.write_text(
            json.dumps(
                report,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        print(f"Отчёт сохранён: {args.output}")


if __name__ == "__main__":
    main()