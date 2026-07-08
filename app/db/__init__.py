from app.db.connection import get_connection
from app.db.schema import init_db
from app.db.niches import get_active_niches
from app.db.stopwords import get_active_stopwords
from app.db.telegram_configs import (
    get_telegram_config_by_company,
    get_active_telegram_configs,
)

from app.db.messages import (
    save_message,
    get_message_by_id,
    get_message_by_tg_id,
    get_reply_chain,
    get_chat_history,
    get_context_chain,
)

from app.db.leads import save_lead_result

from app.db.feedback import (
    update_lead_feedback,
    update_lead_feedback,
    count_final_feedback_since
)

from app.db.embeddings import (
    save_embedding,
    get_messages_without_embeddings,
)

from app.db.dedup import (
    save_seen_message,
    exists_seen_message,
)