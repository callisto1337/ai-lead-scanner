from app.db.leads import save_lead_result
from app.filter import is_lead
from app.metrics import (
    ai_time,
    ai_request,
    lead_detected,
    message_received,
)
from app.types import (
    MessageId,
    NicheWithConfig,
    ProcessMessageResult,
    TgUserId,
)


def process_message(
    clean_text: str,
    message_id: MessageId,
    niche: NicheWithConfig,
    sender_id: TgUserId | None = None,
    sender_name: str | None = None,
    sender_username: str | None = None,
    reply_text: str | None = None,
    reply_sender_id: TgUserId | None = None,
) -> ProcessMessageResult | None:
    message_received.inc()
    ai_request.inc()

    with ai_time.time():
        ai_result = is_lead(
            text=clean_text,
            niche=niche,
            sender_id=sender_id,
            reply_text=reply_text,
            reply_sender_id=reply_sender_id,
        )

    if ai_result is None:
        return None

    lead_result = save_lead_result(
        message_id=message_id,
        niche_id=niche["id"],
        ai_lead=ai_result["lead"],
        description=ai_result.get("description", ""),
        prompt=ai_result.get("prompt"),
        raw_response=ai_result.get("raw_response"),
        niche_score=ai_result.get("niche_score", 0),
        intent_score=ai_result.get("intent_score", 0),
    )

    if lead_result is None:
        raise RuntimeError("Не удалось сохранить результат классификации")

    if ai_result["lead"]:
        lead_detected.inc()

    result: ProcessMessageResult = {
        "lead_result_id": lead_result["id"],
        "lead": ai_result["lead"],
        "description": ai_result["description"],
        "niche_score": ai_result["niche_score"],
        "intent_score": ai_result["intent_score"],
        "reply_author_relation": ai_result.get(
            "reply_author_relation"
        ),
        "sender_id": sender_id,
        "sender_name": sender_name,
        "sender_username": sender_username,
    }

    return result