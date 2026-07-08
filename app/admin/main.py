from fastapi import FastAPI
from sqladmin import Admin, ModelView
from sqlalchemy import create_engine
from fastapi import Form, Request
from fastapi.responses import HTMLResponse
from sqladmin import BaseView, expose

from app.bootstrap import bootstrap_app
from app.admin.models import (
    Company,
    Niche,
    NicheConfig,
    NicheKeyword,
    NicheBlacklist,
    LeadDestination,
    GlobalStopword,
    TelegramConfig
)
from app.db.niches import get_niches_for_select, add_niche_blacklist_bulk, add_niche_keywords_bulk
from app.settings import DATABASE_URL


bootstrap_app()

app = FastAPI(title="Lead Scanner Admin")

sqlalchemy_url = DATABASE_URL.replace(
    "postgresql://",
    "postgresql+psycopg://",
)

engine = create_engine(sqlalchemy_url)

admin = Admin(
    app=app,
    engine=engine,
    title="Lead Scanner Admin",
)


class CompanyAdmin(ModelView, model=Company):
    name = "Компания"
    name_plural = "Компании"

    column_list = [
        Company.id,
        Company.name,
        Company.slug,
        Company.is_active,
    ]

    form_columns = [
        Company.name,
        Company.slug,
        Company.is_active,
    ]


class NicheAdmin(ModelView, model=Niche):
    name = "Ниша"
    name_plural = "Ниши"

    column_list = [
        Niche.id,
        Niche.company,
        Niche.name,
        Niche.slug,
        Niche.is_active,
    ]

    form_columns = [
        Niche.company,
        Niche.name,
        Niche.slug,
        Niche.is_active,
    ]


class NicheConfigAdmin(ModelView, model=NicheConfig):
    name = "Конфиг ниши"
    name_plural = "Конфиги ниш"

    column_list = [
        NicheConfig.id,
        NicheConfig.niche,
        NicheConfig.about,
        NicheConfig.extra_instructions,
    ]

    form_columns = [
        NicheConfig.niche,
        NicheConfig.about,
        NicheConfig.extra_instructions,
    ]


class NicheKeywordAdmin(ModelView, model=NicheKeyword):
    name = "Ключевая фраза"
    name_plural = "Ключевые фразы"

    column_list = [
        NicheKeyword.id,
        NicheKeyword.niche_id,
        NicheKeyword.phrase,
        NicheKeyword.is_active,
    ]

    form_columns = [
        NicheKeyword.niche_id,
        NicheKeyword.phrase,
        NicheKeyword.is_active,
    ]


class NicheBlacklistAdmin(ModelView, model=NicheBlacklist):
    name = "Blacklist фраза"
    name_plural = "Blacklist фразы"

    column_list = [
        NicheBlacklist.id,
        NicheBlacklist.niche_id,
        NicheBlacklist.phrase,
        NicheBlacklist.is_active,
    ]

    form_columns = [
        NicheBlacklist.niche_id,
        NicheBlacklist.phrase,
        NicheBlacklist.is_active,
    ]


class LeadDestinationAdmin(ModelView, model=LeadDestination):
    name = "Куда отправлять лиды"
    name_plural = "Куда отправлять лиды"

    column_list = [
        LeadDestination.id,
        LeadDestination.niche_id,
        LeadDestination.telegram_chat_id,
        LeadDestination.telegram_topic_id,
        LeadDestination.is_active,
    ]

    form_columns = [
        LeadDestination.niche_id,
        LeadDestination.telegram_chat_id,
        LeadDestination.telegram_topic_id,
        LeadDestination.is_active,
    ]


class BulkPhrasesAdmin(BaseView):
    name = "Массовые фразы"
    icon = "fa-solid fa-list"

    @expose("/bulk-phrases", methods=["GET", "POST"])
    async def bulk_phrases(self, request: Request):
        message = ""

        if request.method == "POST":
            form = await request.form()

            niche_id = int(form["niche_id"])
            target = form["target"]
            text = form["text"]

            phrases = text.splitlines()

            if target == "keywords":
                added = add_niche_keywords_bulk(niche_id, phrases)
                message = f"Добавлено ключевых фраз: {added}. Дубли пропущены."
            elif target == "blacklist":
                added = add_niche_blacklist_bulk(niche_id, phrases)
                message = f"Добавлено blacklist-фраз: {added}. Дубли пропущены."
            else:
                message = "Ошибка: неизвестный тип списка."

        niches = get_niches_for_select()

        niche_options = "\n".join(
            f'<option value="{niche["id"]}">{niche["company_name"]} / {niche["name"]}</option>'
            for niche in niches
        )

        message_html = ""

        if message:
            message_html = f"""
            <div style="padding: 12px; background: #e8f5e9; border: 1px solid #a5d6a7; margin-bottom: 16px;">
                {message}
            </div>
            """

        return HTMLResponse(f"""
        <!doctype html>
        <html lang="ru">
        <head>
            <meta charset="utf-8">
            <title>Массовые фразы</title>
        </head>
        <body style="font-family: Arial, sans-serif; max-width: 900px; margin: 40px auto;">
            <p>
                <a href="/admin">← Назад в админку</a>
            </p>

            <h1>Массовое добавление фраз</h1>

            {message_html}

            <form method="post">
                <div style="margin-bottom: 16px;">
                    <label>
                        <strong>Ниша</strong><br>
                        <select name="niche_id" required style="width: 100%; padding: 8px;">
                            {niche_options}
                        </select>
                    </label>
                </div>

                <div style="margin-bottom: 16px;">
                    <label>
                        <strong>Куда добавить</strong><br>
                        <select name="target" required style="width: 100%; padding: 8px;">
                            <option value="keywords">Ключевые фразы</option>
                            <option value="blacklist">Blacklist фразы</option>
                        </select>
                    </label>
                </div>

                <div style="margin-bottom: 16px;">
                    <label>
                        <strong>Фразы, каждая с новой строки</strong><br>
                        <textarea
                            name="text"
                            rows="18"
                            required
                            style="width: 100%; padding: 8px; font-family: monospace;"
                            placeholder="Честный знак&#10;маркировка остатков&#10;КИЗ&#10;DataMatrix"
                        ></textarea>
                    </label>
                </div>

                <button type="submit" style="padding: 10px 18px;">
                    Сохранить
                </button>
            </form>
        </body>
        </html>
        """)


class GlobalStopwordAdmin(ModelView, model=GlobalStopword):
    name = "Глобальное стоп-слово"
    name_plural = "Глобальные стоп-слова"

    column_list = [
        GlobalStopword.id,
        GlobalStopword.phrase,
        GlobalStopword.is_active,
    ]

    form_columns = [
        GlobalStopword.phrase,
        GlobalStopword.is_active,
    ]


class TelegramConfigAdmin(ModelView, model=TelegramConfig):
    name = "Telegram настройки"
    name_plural = "Telegram настройки"

    column_list = [
        TelegramConfig.id,
        TelegramConfig.company,
        TelegramConfig.chat_id,
        TelegramConfig.leads_topic_id,
        TelegramConfig.metrics_topic_id,
        TelegramConfig.is_active,
    ]

    form_columns = [
        TelegramConfig.company,
        TelegramConfig.chat_id,
        TelegramConfig.leads_topic_id,
        TelegramConfig.metrics_topic_id,
        TelegramConfig.is_active,
    ]


admin.add_view(GlobalStopwordAdmin)
admin.add_view(CompanyAdmin)
admin.add_view(NicheAdmin)
admin.add_view(TelegramConfigAdmin)
admin.add_view(NicheConfigAdmin)
admin.add_view(NicheKeywordAdmin)
admin.add_view(NicheBlacklistAdmin)
admin.add_view(LeadDestinationAdmin)
admin.add_view(BulkPhrasesAdmin)