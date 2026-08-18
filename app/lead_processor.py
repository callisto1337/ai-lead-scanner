from app.db.leads import save_lead_result
from app.filter import is_lead
from app.metrics import (
    ai_time,
    ai_request,
    lead_detected,
    message_received,
    borderline_detected,
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
    labels = {
        "company_id": str(niche["company_id"]),
        "niche_id": str(niche["id"]),
    }

    message_received.labels(**labels).inc()
    ai_request.labels(**labels).inc()

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
        verdict=ai_result["verdict"],
        niche_match=ai_result["niche_match"],
        intent_match=ai_result["intent_match"],
    )

    if lead_result is None:
        raise RuntimeError("Не удалось сохранить результат классификации")

    if ai_result["verdict"] == "lead":
        lead_detected.labels(**labels).inc()
    elif ai_result["verdict"] == "borderline":
        borderline_detected.labels(**labels).inc()

    result: ProcessMessageResult = {
        "lead_result_id": lead_result["id"],
        "lead": ai_result["lead"],
        "verdict": ai_result["verdict"],
        "description": ai_result["description"],
        "niche_match": ai_result["niche_match"],
        "intent_match": ai_result["intent_match"],
        "reply_author_relation": ai_result.get(
            "reply_author_relation"
        ),
        "sender_id": sender_id,
        "sender_name": sender_name,
        "sender_username": sender_username,
    }

    return result