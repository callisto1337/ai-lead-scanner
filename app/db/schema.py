from app.db.connection import get_connection


def init_db():
    with get_connection() as conn:
        conn.execute("CREATE SCHEMA IF NOT EXISTS public;")
        conn.execute("SET search_path TO public;")

        conn.execute(
            """
            CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;
            """
        )

        conn.execute("CREATE SCHEMA IF NOT EXISTS phoenix;")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages
            (
                id            TEXT PRIMARY KEY,

                reply_to_id   TEXT REFERENCES messages (id),
                reply_sender_id BIGINT,

                tg_message_id BIGINT      NOT NULL,
                tg_chat_id    BIGINT      NOT NULL,

                text          TEXT        NOT NULL,

                user_id       BIGINT,
                user_link     TEXT,
                source_link   TEXT,

                tg_created_at TIMESTAMPTZ,
                created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),

                UNIQUE (tg_chat_id, tg_message_id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS message_feedback_events
            (
                id                  BIGSERIAL PRIMARY KEY,
                message_id          TEXT        NOT NULL REFERENCES messages (id),
                previous_feedback   TEXT,
                new_feedback        TEXT        NOT NULL,
                previous_human_lead BOOLEAN,
                new_human_lead      BOOLEAN,
                rated_at            TIMESTAMPTZ NOT NULL,
                rated_by_id         BIGINT,
                rated_by_username   TEXT,
                rated_by_name       TEXT,
                created_at          TIMESTAMPTZ NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS message_embeddings
            (
                id         SERIAL PRIMARY KEY,
                message_id TEXT NOT NULL
                    REFERENCES messages (id)
                        ON DELETE CASCADE,
                embedding  vector(384),
                model      TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE (message_id, model)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS seen_messages
            (
                id              SERIAL PRIMARY KEY,
                hash            TEXT,
                normalized_text TEXT,
                created_at      TIMESTAMPTZ NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS blacklist_users
            (
                id         BIGSERIAL PRIMARY KEY,
                user_id    BIGINT      NOT NULL UNIQUE,
                created_at TIMESTAMPTZ NOT NULL,
                created_by BIGINT,
                reason     TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS companies
            (
                id         BIGSERIAL PRIMARY KEY,
                name       TEXT        NOT NULL,
                slug       TEXT        NOT NULL UNIQUE,
                is_active  BOOLEAN     NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS niches
            (
                id         BIGSERIAL PRIMARY KEY,
                company_id BIGINT      NOT NULL REFERENCES companies (id) ON DELETE CASCADE,

                name       TEXT        NOT NULL,
                slug       TEXT        NOT NULL,
                is_active  BOOLEAN     NOT NULL DEFAULT TRUE,

                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

                UNIQUE (company_id, slug)
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS niche_configs
            (
                id              BIGSERIAL PRIMARY KEY,
                niche_id        BIGINT      NOT NULL REFERENCES niches (id) ON DELETE CASCADE UNIQUE,

                about           TEXT        NOT NULL DEFAULT '',
                extra_instructions TEXT        NOT NULL DEFAULT '',

                created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS niche_keywords
            (
                id         BIGSERIAL PRIMARY KEY,
                niche_id   BIGINT      NOT NULL REFERENCES niches (id) ON DELETE CASCADE,

                phrase     TEXT        NOT NULL,
                is_active  BOOLEAN     NOT NULL DEFAULT TRUE,

                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

                UNIQUE (niche_id, phrase)
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS niche_blacklist
            (
                id         BIGSERIAL PRIMARY KEY,
                niche_id   BIGINT      NOT NULL REFERENCES niches (id) ON DELETE CASCADE,

                phrase     TEXT        NOT NULL,
                is_active  BOOLEAN     NOT NULL DEFAULT TRUE,

                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

                UNIQUE (niche_id, phrase)
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS lead_results
            (
                id                BIGSERIAL PRIMARY KEY,

                message_id        TEXT        NOT NULL REFERENCES messages (id) ON DELETE CASCADE,
                niche_id          BIGINT      NOT NULL REFERENCES niches (id) ON DELETE CASCADE,

                ai_lead           BOOLEAN NOT NULL DEFAULT FALSE,
                niche_score       INTEGER NOT NULL DEFAULT 0,
                intent_score      INTEGER NOT NULL DEFAULT 0,
                description       TEXT    NOT NULL DEFAULT '',

                raw_response      JSONB,
                prompt            TEXT,

                human_lead        BOOLEAN,
                feedback          TEXT,

                sent_to_telegram  BOOLEAN     NOT NULL DEFAULT FALSE,
                sent_at           TIMESTAMPTZ,

                detected_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
                rated_at          TIMESTAMPTZ,
                rated_by_id       BIGINT,
                rated_by_username TEXT,
                rated_by_name     TEXT,

                created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),

                UNIQUE (message_id, niche_id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS lead_feedback_events
            (
                id                  BIGSERIAL PRIMARY KEY,

                lead_result_id      BIGINT      NOT NULL REFERENCES lead_results (id) ON DELETE CASCADE,

                previous_feedback   TEXT,
                new_feedback        TEXT        NOT NULL,

                previous_human_lead BOOLEAN,
                new_human_lead      BOOLEAN,

                rated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
                rated_by_id         BIGINT,
                rated_by_username   TEXT,
                rated_by_name       TEXT,

                created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS lead_destinations
            (
                id                BIGSERIAL PRIMARY KEY,
                niche_id          BIGINT      NOT NULL REFERENCES niches (id) ON DELETE CASCADE,

                telegram_chat_id  BIGINT      NOT NULL,
                telegram_topic_id BIGINT,

                is_active         BOOLEAN     NOT NULL DEFAULT TRUE,

                created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),

                UNIQUE (niche_id, telegram_chat_id, telegram_topic_id)
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS global_stopwords
            (
                id         BIGSERIAL PRIMARY KEY,
                phrase     TEXT        NOT NULL UNIQUE,
                is_active  BOOLEAN     NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS telegram_configs
            (
                id               BIGSERIAL PRIMARY KEY,

                company_id       BIGINT      NOT NULL REFERENCES companies (id) ON DELETE CASCADE UNIQUE,

                chat_id          BIGINT      NOT NULL,
                leads_topic_id   BIGINT,
                metrics_topic_id BIGINT,

                is_active        BOOLEAN     NOT NULL DEFAULT TRUE,

                created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_lead_results_detected_at
                ON lead_results (detected_at)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_lead_results_rated_at
                ON lead_results (rated_at)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_lead_results_message_id
                ON lead_results (message_id)
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_lead_results_niche_id
                ON lead_results (niche_id)
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_lead_feedback_events_lead_result_id
                ON lead_feedback_events (lead_result_id)
            """
        )