from app.prefilter import prefilter_message
from app.filter import is_lead
from app.metrics import (
    message_received,
    spam_detected,
    lead_detected,
    ai_request,
    AI_TIME
)


def process_message(
    clean_text: str,
    tg_chat_id: int,
    tg_message_id: int,
    reply_tg_message_id: int | None = None
) -> dict | None:
    message_received()

    prefilter_result = prefilter_message(clean_text)

    if not prefilter_result["ok"]:
        spam_detected()

        print(f"❌ {prefilter_result['reason']}", flush=True)

        return None

    ai_request()

    with AI_TIME.time():
        result = is_lead(
            clean_text,
            tg_chat_id,
            tg_message_id,
            reply_tg_message_id
    )

    if not result:
        return None

    if result["lead"]:
        lead_detected()

    return result
