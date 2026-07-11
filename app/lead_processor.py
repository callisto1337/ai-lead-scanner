from app.filter import is_lead
from app.db.leads import save_lead_result
from app.metrics import (
    message_received,
    lead_detected,
    ai_request,
    AI_TIME
)


def process_message(
    clean_text: str,
    message_id: str,
    tg_chat_id: int,
    tg_message_id: int,
    niche: dict,
    reply_tg_message_id: int | None = None,
    reply_text: str | None = None,
) -> dict | None:
    message_received.inc()

    ai_request.inc()

    with AI_TIME.time():
        ai_result = is_lead(
            text=clean_text,
            tg_chat_id=tg_chat_id,
            tg_message_id=tg_message_id,
            niche=niche,
            reply_tg_message_id=reply_tg_message_id,
            reply_text=reply_text,
        )

    if not ai_result:
        return None

    lead_result = save_lead_result(
        message_id=message_id,
        niche_id=niche["id"],
        ai_lead=bool(ai_result["lead"]),
        description=ai_result.get("description", ""),
        prompt=ai_result.get("prompt"),
        raw_response=ai_result.get("raw_response"),
    )

    if ai_result["lead"]:
        lead_detected.inc()

    return {
        **ai_result,
        "lead_result_id": lead_result["id"],
        "niche_id": niche["id"],
        "niche_name": niche["name"],
        "company_name": niche["company_name"],
    }