from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypedDict

import app.filter as lead_filter
from app.types import NicheWithConfig
from app.db.niches import get_active_niches_with_config

def get_niche_by_id(niche_id: int) -> NicheWithConfig:
    niches = get_active_niches_with_config()

    for niche in niches:
        if int(niche["id"]) == niche_id:
            return niche

    raise RuntimeError(
        f"Активная ниша с id={niche_id} не найдена"
    )


Expected = Literal["lead", "not_lead"]
Actual = Literal["lead", "not_lead", "error"]
CaseGroup = Literal["good", "bad", "borderline"]


class PromptCaseResult(TypedDict):
    name: str
    group: CaseGroup
    expected: Expected
    actual: Actual
    passed: bool
    niche_score: int | None
    intent_score: int | None
    description: str
    prompt_version: str | None
    note: str


@dataclass(frozen=True)
class PromptCase:
    name: str
    text: str
    expected: Expected
    group: CaseGroup
    reply_text: str | None = None
    same_reply_author: bool | None = None
    note: str = ""


CASES: list[PromptCase] = [
    PromptCase(
        name='good_import_aggregation',
        text='После импорта нужно ввести в оборот 5000 единиц. Можно ли создать агрегационные коды, чтобы не сканировать каждый КМ поштучно?',
        expected='lead',
        group='good',
        note='Из старого регрессионного набора.',
    ),
    PromptCase(
        name='good_marking_deadline',
        text='Подскажите, с какой даты обязательна маркировка глюкометров и тест-полосок? Они ещё во втором этапе эксперимента?',
        expected='lead',
        group='good',
        note='Из старого регрессионного набора.',
    ),
    PromptCase(
        name='good_promo_box',
        text='Нужно ли наносить коды маркировки на каждое вложение, если товар продаётся только целиком как промобокс?',
        expected='not_lead',
        group='good',
        note='Из старого регрессионного набора.',
    ),
    PromptCase(
        name='good_supplier_must_mark',
        text='Все новые игрушки теперь поставщик должен передавать уже маркированными или нам нужно заказывать коды самостоятельно?',
        expected='lead',
        group='good',
        note='Из старого регрессионного набора.',
    ),
    PromptCase(
        name='good_chz_error',
        text='у меня ошибка в ЧЗ, что делать?',
        expected='lead',
        group='good',
        note='Из ранее присланного prompt_test_full.py.',
    ),
    PromptCase(
        name='good_codes_error',
        text='не могу выпустить коды маркировки, постоянно выходит ошибка',
        expected='lead',
        group='good',
        note='Из ранее присланного prompt_test_full.py.',
    ),
    PromptCase(
        name='good_registration',
        text='как зарегистрировать ИП в Честном знаке?',
        expected='lead',
        group='good',
        note='Из ранее присланного prompt_test_full.py.',
    ),
    PromptCase(
        name='good_gs1',
        text='подскажите, как пройти регистрацию в GS1',
        expected='lead',
        group='good',
        note='Из ранее присланного prompt_test_full.py.',
    ),
    PromptCase(
        name='good_tnved',
        text='нужно проверить ТН ВЭД и понять, попадает ли товар под маркировку',
        expected='lead',
        group='good',
        note='Из ранее присланного prompt_test_full.py.',
    ),
    PromptCase(
        name='good_product_required',
        text='как понять, нужно ли маркировать мой товар?',
        expected='lead',
        group='good',
        note='Из ранее присланного prompt_test_full.py.',
    ),
    PromptCase(
        name='good_cosmetics',
        text='начинаем продавать косметику, что нужно сделать по маркировке?',
        expected='lead',
        group='good',
        note='Из ранее присланного prompt_test_full.py.',
    ),
    PromptCase(
        name='good_leftovers',
        text='как правильно начать маркировку остатков в рознице?',
        expected='lead',
        group='good',
        note='Из ранее присланного prompt_test_full.py.',
    ),
    PromptCase(
        name='good_cabinet',
        text='не получается настроить личный кабинет Честного знака',
        expected='lead',
        group='good',
        note='Из ранее присланного prompt_test_full.py.',
    ),
    PromptCase(
        name='good_print_codes',
        text='как подготовить и распечатать коды DataMatrix?',
        expected='lead',
        group='good',
        note='Из ранее присланного prompt_test_full.py.',
    ),
    PromptCase(
        name='good_upd',
        text='как передать УПД с кодами маркировки?',
        expected='lead',
        group='good',
        note='Из ранее присланного prompt_test_full.py.',
    ),
    PromptCase(
        name='good_marketplace_codes',
        text='как передать коды маркировки на Озон?',
        expected='lead',
        group='good',
        note='Из ранее присланного prompt_test_full.py.',
    ),
    PromptCase(
        name='good_training',
        text='кто может обучить работе в Честном знаке?',
        expected='lead',
        group='good',
        note='Из ранее присланного prompt_test_full.py.',
    ),
    PromptCase(
        name='good_reply_other_own_problem',
        text='Я уже написала в поддержку, но КИЗ ввели в оборот. Что теперь делать, пока не отправлять товар?',
        expected='lead',
        group='good',
        reply_text='Напишите им, они должны разобраться.',
        same_reply_author=False,
        note='CURRENT_USER явно описывает собственную проблему, несмотря на reply другого автора.',
    ),
    PromptCase(
        name='good_under_key',
        text='помогите срочно с ЧЗ под ключ',
        expected='lead',
        group='good',
        note='Из ранее присланного prompt_test_full.py.',
    ),
    PromptCase(
        name='good_kiz_help',
        text='кто делает КИЗ для ЧЗ? нужна помощь',
        expected='lead',
        group='good',
        note='Из ранее присланного prompt_test_full.py.',
    ),
    PromptCase(
        name='good_upd_from_wb',
        text='как передать упд от вб?',
        expected='lead',
        group='good',
        note='DB lead_result_id=107821.',
    ),
    PromptCase(
        name='good_who_helps_chz',
        text='кто помогает с честным знаком ?',
        expected='lead',
        group='good',
        note='DB lead_result_id=36918.',
    ),
    PromptCase(
        name='good_anyone_help_chz',
        text='кто нибудь поможет с честным знаком?',
        expected='lead',
        group='good',
        note='DB lead_result_id=10078.',
    ),
    PromptCase(
        name='good_upd_processing_error',
        text='ошибка при обработке упд честным знаком',
        expected='lead',
        group='good',
        note='DB lead_result_id=22534.',
    ),
    PromptCase(
        name='good_register_chz',
        text='помогите зарегистрироваться в чесном знаке и',
        expected='lead',
        group='good',
        note='DB lead_result_id=19071.',
    ),
    PromptCase(
        name='good_osu_upd',
        text='по осу можно вывести из оборота км через упд?',
        expected='lead',
        group='good',
        note='DB lead_result_id=16397.',
    ),
    PromptCase(
        name='good_codes_puffer_jackets',
        text='добрый день. нужны коды маркировки на пуховики.',
        expected='lead',
        group='good',
        note='DB lead_result_id=72399.',
    ),
    PromptCase(
        name='good_herbal_marking',
        text='здравствуйте! подлежат ли маркировке травяные сборы?',
        expected='lead',
        group='good',
        note='DB lead_result_id=27063.',
    ),
    PromptCase(
        name='good_nk_without_rd',
        text='если в нк написано отсутствует рд, можно маркировать ?',
        expected='lead',
        group='good',
        note='DB lead_result_id=190261.',
    ),
    PromptCase(
        name='good_order_codes_soap',
        text='здравствуйте! подскажите как заказать чз на мыло мойку ?',
        expected='lead',
        group='good',
        note='DB lead_result_id=82064.',
    ),
    PromptCase(
        name='good_order_codes_start',
        text='здравствуйте. как заказать коды маркировки? с чего начать?',
        expected='lead',
        group='good',
        note='DB lead_result_id=91066.',
    ),
    PromptCase(
        name='good_cosmetics_leftovers',
        text='всем привет! нужна помощь с маркировкой остатков косметики.',
        expected='lead',
        group='good',
        note='DB lead_result_id=105245.',
    ),
    PromptCase(
        name='good_sold_kiz_next_steps',
        text='добрый день! подскажите пожалуйста: на «пробу» отправила товар с маркировкой в количестве 1 ед на вб с киз. создала упд по акту приемки,этот товар продался. мои будут какие-то дальнейшие действия? или они его сами уже выводят из оборота?',
        expected='lead',
        group='good',
        note='DB lead_result_id=251629.',
    ),
    PromptCase(
        name='good_fbo_marking_unreadable',
        text='добрый день. если по фбо маркировка не читаетсч,то отправляют возвратом на пвз? штраф есть какой-то?',
        expected='lead',
        group='good',
        note='DB lead_result_id=30473.',
    ),
    PromptCase(
        name='good_same_author_continuation',
        text='А если указали количество 1 вместо 200, как теперь это исправить?',
        expected='lead',
        group='good',
        reply_text='В отчёте о нанесении нужно указывать фактическое количество в переменной характеристике на каждый код.',
        same_reply_author=True,
        note='Тот же автор продолжает собственную задачу.',
    ),
    PromptCase(
        name='bad_reply_other_advice',
        text='Смотреть нужно через личный кабинет Честного знака. Поставщик должен написать в поддержку, другого способа исправить код нет.',
        expected='not_lead',
        group='bad',
        reply_text='Как понять, что у кода нет переменной характеристики? У меня похожая ситуация.',
        same_reply_author=False,
        note='CURRENT_USER консультирует REPLY_USER.',
    ),
    PromptCase(
        name='bad_reply_other_diagnostic',
        text='Декларацию подписали, пошлина списалась, но запись не появилась в реестре?',
        expected='not_lead',
        group='bad',
        reply_text='Подписали документ, а в Честном знаке теперь написано «не найден в реестре».',
        same_reply_author=False,
        note='CURRENT_USER уточняет чужую проблему.',
    ),
    PromptCase(
        name='bad_advice_old_stock',
        text='Поставьте дату производства до начала маркировки и распродайте остатки. ВБ и Ozon товар без КИЗ всё равно не примут.',
        expected='not_lead',
        group='bad',
        reply_text='Как продать остатки без маркировки?',
        same_reply_author=False,
        note='CURRENT_USER даёт совет.',
    ),
    PromptCase(
        name='bad_marketplace_packaging',
        text='Грузоместо — это общая коробка. QR-код клеится только на неё, а на коробках товаров остаются штрихкоды и QR-коды ВБ.',
        expected='not_lead',
        group='bad',
        reply_text='Куда клеить QR-код грузоместа при отгрузке на ПВЗ?',
        same_reply_author=False,
        note='Ответ про логистику маркетплейса.',
    ),
    PromptCase(
        name='bad_gray_goods',
        text='Есть у кого контакты, кто делает Честный знак для серого товара?',
        expected='not_lead',
        group='bad',
        note='Исключённое направление.',
    ),
    PromptCase(
        name='bad_one_c_integration',
        text='Кто может настроить интеграцию Честного знака с 1С, чтобы КМ автоматически передавались по УПД?',
        expected='not_lead',
        group='bad',
        note='Исключённое направление 1С.',
    ),
    PromptCase(
        name='bad_generic_help',
        text='Помогите, кто сможет?',
        expected='not_lead',
        group='bad',
        note='Тема не указана.',
    ),
    PromptCase(
        name='bad_ozon_moderation',
        text='Подскажите, почему карточка товара на Ozon уже второй день на модерации?',
        expected='not_lead',
        group='bad',
        note='Маркетплейс без маркировки.',
    ),
    PromptCase(
        name='bad_printer_recommendation',
        text='Посоветуйте надёжный и недорогой принтер для печати этикеток маркировки, у моего принтера слишком дорогая лента.',
        expected='not_lead',
        group='bad',
        note='Покупка оборудования вне услуг.',
    ),
    PromptCase(
        name='bad_generic_help_emoji',
        text='🙏 пожалуйста, очень поможете!',
        expected='not_lead',
        group='bad',
        note='Тема не указана.',
    ),
    PromptCase(
        name='bad_generic_paid_help',
        text='нужна помощь, кто готов — маякните, в конце по 10 000 даю',
        expected='not_lead',
        group='bad',
        note='Тема не указана.',
    ),
    PromptCase(
        name='bad_generic_task_paid',
        text='дело на пару часов — оплата 12 000 р.',
        expected='not_lead',
        group='bad',
        note='Тема не указана.',
    ),
    PromptCase(
        name='bad_generic_one_task',
        text='народ, кто сейчас готов помочь по одному делу? займет минимум времени',
        expected='not_lead',
        group='bad',
        note='Тема не указана.',
    ),
    PromptCase(
        name='bad_generic_urgent',
        text='срочно нужен человек, пишите в личку',
        expected='not_lead',
        group='bad',
        note='Тема не указана.',
    ),
    PromptCase(
        name='bad_generic_question',
        text='кто-нибудь сталкивался с такой проблемой?',
        expected='not_lead',
        group='bad',
        note='Тема не указана.',
    ),
    PromptCase(
        name='bad_generic_thanks',
        text='спасибо всем, уже разобрался',
        expected='not_lead',
        group='bad',
        note='Потребность уже закрыта.',
    ),
    PromptCase(
        name='bad_sell_codes',
        text='продам готовые коды маркировки недорого',
        expected='not_lead',
        group='bad',
        note='Предложение услуг и готовые коды.',
    ),
    PromptCase(
        name='bad_buy_codes',
        text='куплю готовые коды для обуви без документов',
        expected='not_lead',
        group='bad',
        note='Покупка кодов в обход системы.',
    ),
    PromptCase(
        name='bad_service_offer',
        text='занимаюсь маркировкой под ключ, пишите в личку',
        expected='not_lead',
        group='bad',
        note='CURRENT_USER предлагает свои услуги.',
    ),
    PromptCase(
        name='bad_vacancy',
        text='требуется оператор Честного знака в штат',
        expected='not_lead',
        group='bad',
        note='Поиск сотрудника.',
    ),
    PromptCase(
        name='bad_news',
        text='с сентября вступают новые правила маркировки одежды',
        expected='not_lead',
        group='bad',
        note='Новость без собственной задачи.',
    ),
    PromptCase(
        name='bad_success',
        text='мы наконец-то сами выпустили все коды в ЧЗ',
        expected='not_lead',
        group='bad',
        note='Задача уже решена.',
    ),
    PromptCase(
        name='bad_fbs_cancel_delivery',
        text='добрый вечер! фбс. подскажите пожалуйста, если уже кинул заказ в «доставку», убрать обратно оттуда можно ? или это будет отмена заказа и штраф ?',
        expected='not_lead',
        group='bad',
        note='DB lead_result_id=293985; логистика FBS.',
    ),
    PromptCase(
        name='bad_cancelled_order_courier',
        text='добрый день! работаем по fвs,сегодня отправили товары курьером на ппз и по пути вижу что от одного из заказов клиент отказался. что будет если отгрузить отмененный заказ?',
        expected='not_lead',
        group='bad',
        note='DB lead_result_id=273076; логистика FBS.',
    ),
    PromptCase(
        name='bad_pvz_accepted_cancel',
        text='скажите пожалуйста если пвз приняли уже товар по фбс поставку нельзя отменить?',
        expected='not_lead',
        group='bad',
        note='DB lead_result_id=295144; логистика FBS.',
    ),
    PromptCase(
        name='bad_fbs_not_sent_penalty',
        text='подскажите, сколько штраф за неотправленный заказ по фбс?',
        expected='not_lead',
        group='bad',
        note='DB lead_result_id=288963; штраф FBS.',
    ),
    PromptCase(
        name='bad_cancel_orders_without_penalty',
        text='коллеги, всем привет! работаю только по фбс. территориально в шушары отгружаем. вопрос следующий: мы же можем отменить пришедшие заказы без штрафа?',
        expected='not_lead',
        group='bad',
        note='DB lead_result_id=205611; логистика FBS.',
    ),
    PromptCase(
        name='bad_fbs_18h_penalty',
        text='добрый день подскажите пожалуйста фбс если не отгрузить за 18ч штраф идет сейчас ?',
        expected='not_lead',
        group='bad',
        note='DB lead_result_id=206721; штраф FBS.',
    ),
    PromptCase(
        name='bad_supply_pvz_scan',
        text='подскажите еще раз, будьте добры. я поставку делаю, собираю заказы добавляю туда, но не отгружаю поставку( не нажимаю кнопку), так? в пвз пикнут и сама поставка отгрузится? всё верно ?',
        expected='not_lead',
        group='bad',
        note='DB lead_result_id=251447; процесс поставки WB.',
    ),
    PromptCase(
        name='bad_late_supply_penalty',
        text='подскажите, если поставку не успели привезти через сутки после запланированной даты, ее уже вообще принять не смогут или примут, но со штрафом?',
        expected='not_lead',
        group='bad',
        note='DB lead_result_id=242123; логистика поставки.',
    ),
    PromptCase(
        name='bad_warehouse_overload_cancellations',
        text='здравствуйте, подскажите, пожалуйста, работаем по фбс, в связи с ситуацией в стране, склад перегружен, сортировка задерживается уже с 19.07, заказы в статусе сортировка и если товар не пикнули на складе, заказы отменяются. получается, мы будем платить за отмененный заказ,хотя мы его доставили сразу. что делать в этой ситуации?',
        expected='not_lead',
        group='bad',
        note='DB lead_result_id=198143; логистика FBS.',
    ),
    PromptCase(
        name='bad_alexin_fbs_status',
        text='здравствуйте. фбс, отгружаем поставки каждый день через алексин , статус заказа не меняется . сегодня прилетела одна отмена автоматическая что нам делать с этими заказами,которые не сканируют на складе по их вине .время идет получается все заказы в отмену, за ,что начислят еще штраф 30% от стоимости товара и минусом еще сам товар и работа (свое производство) как выходите из ситуации? через пвз нам неудобно и долго 😭',
        expected='not_lead',
        group='bad',
        note='DB lead_result_id=260453; логистика FBS.',
    ),
    PromptCase(
        name='bad_where_returns_go',
        text='а куда сейчас едут возвраты или отмены если раньше ехали на склады то теперь?',
        expected='not_lead',
        group='bad',
        note='DB lead_result_id=274564; возвраты маркетплейса.',
    ),
    PromptCase(
        name='bad_configure_fbs_return',
        text='можете пожалуйста подсказать когда работаешь по фбс, как настроить, чтобы после отказа покупателем на пвз товар возвращался обратно мне?',
        expected='not_lead',
        group='bad',
        note='DB lead_result_id=187775; логистика FBS.',
    ),
    PromptCase(
        name='bad_fbo_overdelivery_sanctions',
        text='доброе утро! подскажите плиз, какие санкции накладывает вб, если по фбо заявке привезти сильно больше товара, чем заявлено',
        expected='not_lead',
        group='bad',
        note='DB lead_result_id=241469; поставка FBO.',
    ),
    PromptCase(
        name='bad_pvz_delivery_fee',
        text='если отправлять через пвз по 50 товаров, чтобы не платить 75р',
        expected='not_lead',
        group='bad',
        note='Ранее присланный пример; стоимость логистики.',
    ),
    PromptCase(
        name='bad_spp_fbo_stock',
        text='а как расчитывается спп если на фбо целых есть наличие?',
        expected='not_lead',
        group='bad',
        note='DB lead_result_id=199190; СПП и остатки маркетплейса.',
    ),
    PromptCase(
        name='bad_fbo_fbs_simultaneously',
        text='можно продавать по фбо и фбс одновременно?',
        expected='not_lead',
        group='bad',
        note='Ранее присланный пример; схема продаж маркетплейса.',
    ),
    PromptCase(
        name='bad_move_stock_koledino',
        text='можно с Коледино переместить остатки на другой склад?',
        expected='not_lead',
        group='bad',
        note='Ранее присланный пример; остатки склада маркетплейса.',
    ),
    PromptCase(
        name='bad_fbo_fbs_priority',
        text='какой приоритет у товара, если он есть одновременно по фбо и фбс?',
        expected='not_lead',
        group='bad',
        note='Ранее присланный пример; логика маркетплейса.',
    ),
    PromptCase(
        name='borderline_return_code_1c',
        text='Товар вернули, КМ уже выбыл. Как вернуть код маркировки в оборот, если 1С пишет, что КМ не принадлежит нашему юрлицу?',
        expected='not_lead',
        group='borderline',
        note='Проверить: задача по маркировке, но присутствует исключённое направление 1С.',
    ),
    PromptCase(
        name='borderline_recommend_upd_bot',
        text='Посоветуйте, пожалуйста, бота для передачи УПД в Честный знак.',
        expected='not_lead',
        group='borderline',
        note='Проверить: УПД относится к нише, но запрос именно про стороннего бота.',
    ),
    PromptCase(
        name='borderline_chz_definition',
        text='что такое Честный знак?',
        expected='not_lead',
        group='borderline',
        note='Проверить: общий информационный вопрос без конкретной задачи.',
    ),
    PromptCase(
        name='borderline_mercury_registration',
        text='нужно зарегистрироваться в Меркурии, кто подскажет порядок?',
        expected='not_lead',
        group='borderline',
        note='Проверить: соседняя система, не Честный знак.',
    ),
    PromptCase(
        name='borderline_short_fbs_chz',
        text='по фбс с чз да',
        expected='not_lead',
        group='borderline',
        note='DB lead_result_id=154445. Короткое сообщение без явной задачи; в production отсеется по длине.',
    ),
    PromptCase(
        name='borderline_short_chz_or_kiz',
        text='честный знак или киз нужно ?',
        expected='not_lead',
        group='borderline',
        note='DB lead_result_id=11364. Контекст reply неизвестен; в production отсеется по длине.',
    ),
    PromptCase(
        name='borderline_card_published',
        text='здравствуйте, карточка опубликована?',
        expected='not_lead',
        group='borderline',
        note='DB lead_result_id=16561. Без reply тема не подтверждена.',
    ),
    PromptCase(
        name='borderline_shk_skip_changed',
        text='добрый день!само шк пропуска поменялось?',
        expected='not_lead',
        group='borderline',
        note='DB lead_result_id=22707. Неясно, относится ли вопрос к маркировке.',
    ),
    PromptCase(
        name='borderline_output_button_missing',
        text='у меня пропала кнопка « вывести сейчас « 🥹',
        expected='lead',
        group='borderline',
        note='DB lead_result_id=187668. Проверить, означает ли кнопка вывод из оборота в ЧЗ.',
    ),
    PromptCase(
        name='borderline_scan_chz',
        text='посоветуйте пожалуйста чем отсканировать чз',
        expected='not_lead',
        group='borderline',
        note='DB lead_result_id=22929. Возможно запрос оборудования вне услуг.',
    ),
    PromptCase(
        name='borderline_marking_chz_fbs',
        text='добрый день, подскажите как маркируете чз по fвs?',
        expected='lead',
        group='borderline',
        note='DB lead_result_id=127883. Есть маркировка, но запрос может быть общим обсуждением.',
    ),
    PromptCase(
        name='borderline_code_missing',
        text='здравствуйте. в том то и дело кода у меня этого нет )',
        expected='not_lead',
        group='borderline',
        note='DB lead_result_id=73634. Без reply тема и собственная задача не восстановлены.',
    ),
    PromptCase(
        name='borderline_declaration_registry',
        text='дс подписали, пошлина списалась, и не появился в реестре?',
        expected='not_lead',
        group='borderline',
        note='DB lead_result_id=107097. Вероятнее сертификация, а не маркировка.',
    ),
    PromptCase(
        name='borderline_money_withdraw_button',
        text='а как деньги теперь выводить? кнопка за 4% пропала',
        expected='not_lead',
        group='borderline',
        note='DB lead_result_id=202648. Финансы маркетплейса.',
    ),
    PromptCase(
        name='borderline_same_day_withdrawal',
        text='кнопка вывода день в день у всех пропала или я один такой?',
        expected='not_lead',
        group='borderline',
        note='DB lead_result_id=203145. Неясное слово «вывод», вероятнее финансы.',
    ),
    PromptCase(
        name='borderline_return_cancel',
        text='если сделали возврат товара, отменить можно?',
        expected='not_lead',
        group='borderline',
        note='DB lead_result_id=196819. Нет признаков маркировки.',
    ),
    PromptCase(
        name='borderline_discrepancy_penalty',
        text='а если расхождения выявляют как штраф начисляют? на последующие заказы если не исправишь ? или на все с первого заказа?',
        expected='not_lead',
        group='borderline',
        note='DB lead_result_id=274872. Без контекста неясно, связаны ли расхождения с маркировкой.',
    ),
    PromptCase(
        name='borderline_short_instruction',
        text='а есть ли инструкция?',
        expected='not_lead',
        group='borderline',
        note='DB lead_result_id=12203. Без reply тема отсутствует; в production отсеется по длине.',
    ),
    PromptCase(
        name='borderline_short_how_to',
        text='подскажите как это сделать?',
        expected='not_lead',
        group='borderline',
        note='DB lead_result_id=13279. Без reply тема отсутствует; в production отсеется по длине.',
    ),
    PromptCase(
        name='borderline_link_only',
        text='httрs://t.mе/с/2093067912/92902',
        expected='not_lead',
        group='borderline',
        note='DB lead_result_id=99794. Только ссылка, reply неизвестен.',
    ),
    PromptCase(
        name='borderline_mark_everything_ourselves',
        text='поомаркировать все самим',
        expected='not_lead',
        group='borderline',
        note='DB lead_result_id=17362. Фрагмент ответа без доступного reply.',
    ),
    PromptCase(
        name='borderline_shushary_remark',
        text='поставка под шушары, заново все маркировать?',
        expected='lead',
        group='borderline',
        note='Ранее присланный похожий пример. Проверить, действительно ли речь о повторной маркировке.',
    ),
    PromptCase(
        name='borderline_white_import_reply',
        text='белый ввоз с чз',
        expected='not_lead',
        group='borderline',
        reply_text='Добрый день! Подскажите, пожалуйста. Я продаю товары на маркетплейсах. Доставка осуществляется через карго, а декларация соответствия оформлена в России как на производителя. В связи с этим не могу по...',
        same_reply_author=False,
        note='CURRENT_USER кратко отвечает REPLY_USER, собственной потребности нет.',
    ),
    PromptCase(
        name='borderline_producer_importer_reply',
        text='как производитель и импортёр',
        expected='not_lead',
        group='borderline',
        reply_text='Добрый день! Подскажите, пожалуйста. Я продаю товары на маркетплейсах. Доставка осуществляется через карго, а декларация соответствия оформлена в России как на производителя. В связи с этим не могу по...',
        same_reply_author=False,
        note='DB lead_result_id=296092. CURRENT_USER продолжает чужое обсуждение.',
    ),
    PromptCase(
        name='borderline_reply_other_explicit_own_problem',
        text='У нас после подписания возникла такая же проблема: пошлина списалась, но записи в реестре нет. Что делать?',
        expected='lead',
        group='borderline',
        reply_text='Подписали документ, а в Честном знаке теперь написано «не найден в реестре».',
        same_reply_author=False,
        note='Проверить: CURRENT_USER явно говорит о своей аналогичной проблеме, но тема может относиться к сертификации.',
    ),
]


def relation_ids(case: PromptCase) -> tuple[int | None, int | None]:
    if case.reply_text is None:
        return 1001, None

    if case.same_reply_author is True:
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
            "group": case.group,
            "expected": case.expected,
            "actual": "error",
            "passed": False,
            "niche_score": None,
            "intent_score": None,
            "description": "Модель не вернула результат",
            "prompt_version": None,
            "note": case.note,
        }

    actual: Actual = "lead" if result["lead"] else "not_lead"

    return {
        "name": case.name,
        "group": case.group,
        "expected": case.expected,
        "actual": actual,
        "passed": actual == case.expected,
        "niche_score": result["niche_score"],
        "intent_score": result["intent_score"],
        "description": result["description"],
        "prompt_version": result["prompt_version"],
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

    niche = get_niche_by_id(args.niche_id)

    results: list[PromptCaseResult] = []

    group_counts = {
        "good": sum(case.group == "good" for case in CASES),
        "bad": sum(case.group == "bad" for case in CASES),
        "borderline": sum(case.group == "borderline" for case in CASES),
    }

    print(
        "\n"
        f"Количество кейсов: {len(CASES)} "
        f"(good={group_counts['good']}, "
        f"bad={group_counts['bad']}, "
        f"borderline={group_counts['borderline']})\n"
    )

    for index, case in enumerate(CASES, start=1):
        result = run_case(case, niche)
        results.append(result)

        marker = "✅" if result["passed"] else "❌"

        print(
            f"{marker} {index:03d}. [{case.group}] {case.name}\n"
            f"   expected={result['expected']} "
            f"actual={result['actual']}\n"
            f"   niche={result['niche_score']} "
            f"intent={result['intent_score']}\n"
            f"   {result['description']}\n"
            f"   note={case.note}\n"
        )

    strict_results = [
        result
        for result in results
        if result["group"] != "borderline"
    ]
    borderline_results = [
        result
        for result in results
        if result["group"] == "borderline"
    ]

    strict_passed = sum(result["passed"] for result in strict_results)
    strict_failed = len(strict_results) - strict_passed

    borderline_matched = sum(
        result["passed"]
        for result in borderline_results
    )

    total_passed = sum(result["passed"] for result in results)
    total_failed = len(results) - total_passed

    print("-" * 72)
    print(
        f"Строгие кейсы: {strict_passed}/{len(strict_results)} успешно, "
        f"ошибок: {strict_failed}"
    )
    print(
        "Спорные кейсы: "
        f"{borderline_matched}/{len(borderline_results)} "
        "совпали с предварительной оценкой"
    )
    print(
        f"Всего: {total_passed}/{len(results)} совпадений, "
        f"расхождений: {total_failed}"
    )

    if args.output is not None:
        report = {
            "niche_id": args.niche_id,
            "strict_passed": strict_passed,
            "strict_failed": strict_failed,
            "borderline_matched": borderline_matched,
            "total_passed": total_passed,
            "total_failed": total_failed,
            "total": len(results),
            "group_counts": group_counts,
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
