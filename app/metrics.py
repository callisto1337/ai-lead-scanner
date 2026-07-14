from prometheus_client import Counter, Histogram, start_http_server


message_received = Counter(
    "lead_scanner_messages_received_total",
    "Total received Telegram messages",
)

ai_request = Counter(
    "lead_scanner_ai_requests_total",
    "Total AI classification requests",
)

lead_detected = Counter(
    "lead_scanner_leads_detected_total",
    "Total AI detected leads",
)

spam_detected = Counter(
    "lead_scanner_spam_detected_total",
    "Total messages rejected by prefilter/spam filters",
)

telegram_send_errors = Counter(
    "lead_scanner_telegram_send_errors_total",
    "Total Telegram send errors",
)

feedback_total = Counter(
    "lead_scanner_feedback_total",
    "Total operator feedback events",
    ["feedback"],
)

AI_TIME = Histogram(
    "lead_scanner_ai_duration_seconds",
    "AI request duration in seconds",
)

user_lead_cooldown_skipped = Counter(
    "lead_scanner_user_cooldown_skipped_total",
    "Messages skipped because the user already produced a lead during cooldown",
    ["company_id", "niche_id"],
)


def start_metrics(port: int, service_name: str = "app") -> None:
    start_http_server(port)

    print(
        f"📊 {service_name} metrics started on :{port}/metrics",
        flush=True,
    )