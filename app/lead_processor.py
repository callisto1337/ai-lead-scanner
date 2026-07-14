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
    niche: dict,
    sender_id: int | None = None,
    reply_text: str | None = None,
    reply_sender_id: int | None = None,
) -> dict | None:
    message_received.inc()
    ai_request.inc()

    with AI_TIME.time():
        ai_result = is_lead(
            text=clean_text,
            niche=niche,
            sender_id=sender_id,
            reply_text=reply_text,
            reply_sender_id=reply_sender_id,
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
        niche_score=ai_result.get("niche_score" , 0),
        intent_score=ai_result.get("intent_score", 0),
    )

    if ai_result["lead"]:
        lead_detected.inc()

    return {
        "lead_result_id": lead_result["id"],
        "lead": ai_result["lead"],
        "description": ai_result["description"],
        "niche_score": ai_result["niche_score"],
        "intent_score": ai_result["intent_score"],
        "reply_author_relation": ai_result.get("reply_author_relation"),
    }