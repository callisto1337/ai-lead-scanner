from prometheus_client import (
    start_http_server,
    Counter,
    Histogram
)

# --------------------
# Метрики
# --------------------

MESSAGES = Counter(
    "messages_total",
    "All received messages"
)

SPAM = Counter(
    "spam_total",
    "Filtered spam messages"
)

LEADS = Counter(
    "leads_total",
    "Detected leads"
)

LEADS_APPROVED = Counter(
    "leads_approved_total",
    "Approved leads by human"
)

LEADS_REJECTED = Counter(
    "leads_rejected_total",
    "Rejected leads by human"
)

LEADS_SKIPPED = Counter(
    "leads_skipped_total",
    "Skipped leads by human"
)

LEADS_BLOCKED = Counter(
    "leads_blocked_total",
    "Blocked leads by human"
)

AI_REQUESTS = Counter(
    "ai_requests_total",
    "Requests sent to AI"
)

AI_TIME = Histogram(
    "ai_response_seconds",
    "AI response time"
)


def start_metrics(port: int = 8000):
    """
    Запускает HTTP сервер Prometheus
    """
    start_http_server(port)
    print(f"📊 Запуск сбора метрик", flush=True)


def message_received():
    MESSAGES.inc()


def spam_detected():
    SPAM.inc()


def lead_detected():
    LEADS.inc()


def ai_request():
    AI_REQUESTS.inc()


def lead_approved():
    LEADS_APPROVED.inc()


def lead_rejected():
    LEADS_REJECTED.inc()


def lead_skipped():
    LEADS_SKIPPED.inc()


def lead_blocked():
    LEADS_BLOCKED.inc()
