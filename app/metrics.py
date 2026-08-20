from prometheus_client import Counter, Histogram, start_http_server, Gauge

message_received = Counter(
    "lead_scanner_messages_received_total",
    "Всего получено сообщений из Telegram",
    ["company_id", "niche_id"],
)

ai_request = Counter(
    "lead_scanner_ai_requests_total",
    "Всего запросов на классификацию к ИИ",
    ["company_id", "niche_id"],
)

lead_detected = Counter(
    "lead_scanner_leads_detected_total",
    "Всего лидов, найденных ИИ",
    ["company_id", "niche_id"],
)

borderline_detected = Counter(
    "lead_scanner_borderline_detected_total",
    "Всего спорных лидов, найденных ИИ",
    ["company_id", "niche_id"],
)

spam_detected = Counter(
    "lead_scanner_spam_detected_total",
    "Всего сообщений, отклонённых префильтром/спам-фильтрами",
)

telegram_send_errors = Counter(
    "lead_scanner_telegram_send_errors_total",
    "Всего ошибок отправки в Telegram",
)

feedback_total = Counter(
    "lead_scanner_feedback_total",
    "Всего событий обратной связи от оператора",
    ["feedback"],
)

ai_time = Histogram(
    "lead_scanner_ai_duration_seconds",
    "Время ответа ИИ в секундах",
)

user_lead_cooldown_skipped = Counter(
    "lead_scanner_user_cooldown_skipped_total",
    "Сообщения, пропущенные из-за того, что пользователь уже дал лид во время cooldown",
    ["company_id", "niche_id"],
)

chat_priority_skipped = Counter(
    "lead_scanner_chat_priority_skipped_total",
    "Сообщения, пропущенные семплированием по приоритету (ниша, чат)",
    ["company_id", "niche_id"],
)

chat_priority_evaluated = Counter(
    "lead_scanner_chat_priority_evaluated_total",
    "Сообщения, дошедшие до проверки приоритета (знаменатель для доли пропуска)",
    ["company_id", "niche_id"],
)

intent_ai_requests = Counter(
    "lead_scanner_intent_ai_requests_total",
    "Запросы к ИИ по оси intent (те самые, что платные при INTENT_BACKEND=yandex)",
    ["backend"],
)

ai_request_duration_seconds = Histogram(
    "lead_scanner_ai_request_duration_seconds",
    "Время ответа модели",
    buckets=(1, 2, 3, 5, 8, 13, 20, 30, 45, 60, 90),
)

ai_errors = Counter(
    "lead_scanner_ai_errors_total",
    "Ошибки при обращении к модели",
    ["reason"],
)

thinking_retry_total = Counter(
    "lead_scanner_thinking_retry_total",
    "Количество повторных запросов с enable_thinking для неоднозначных осей",
    ["axis"],
)

extraction_empty_total = Counter(
    "lead_scanner_extraction_empty_total",
    "Количество сообщений, где извлечение тем вернуло пустой список "
    "(niche_match='нет' без обращения к модели ниши)",
    ["company_id", "niche_id"],
)

message_queue_size = Gauge(
    "lead_scanner_message_queue_size",
    "Текущее количество сообщений в очереди",
)

prefilter_rejected_total = Counter(
    "lead_scanner_prefilter_rejected_total",
    "Количество сообщений, отклонённых префильтром",
    ["reason"],
)

prefilter_passed_total = Counter(
    "lead_scanner_prefilter_passed_total",
    "Количество сообщений, прошедших префильтр",
)

message_processing_delay_seconds = Histogram(
    name="lead_scanner_message_queue_wait_seconds",
    documentation="Время ожидания сообщения в очереди",
    buckets=(0.1, 0.5, 1, 2, 5, 10, 20, 30, 60, 120, 300),
)


def start_metrics(port: int, service_name: str = "app") -> None:
    start_http_server(port)

    print(
        f"📊 {service_name} metrics started on :{port}/metrics",
        flush=True,
    )