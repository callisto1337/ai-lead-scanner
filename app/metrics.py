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


AI_REQUESTS = Counter(
    "ai_requests_total",
    "Requests sent to AI"
)


AI_TIME = Histogram(
    "ai_response_seconds",
    "AI response time"
)


def start_metrics():
    """
    Запускает HTTP сервер Prometheus
    """
    start_http_server(8000)
    print("📊 Metrics started on :8000")


def message_received():
    MESSAGES.inc()


def spam_detected():
    SPAM.inc()


def lead_detected():
    LEADS.inc()


def ai_request():
    AI_REQUESTS.inc()