import json
import logging
from contextlib import nullcontext
from time import perf_counter
from typing import Any, Callable, ContextManager, Optional, cast

try:
    from phoenix.otel import using_metadata, using_tags  # pyright: ignore[reportMissingImports]
except ImportError:
    using_metadata: Optional[Callable[..., ContextManager[Any]]] = None
    using_tags: Optional[Callable[..., ContextManager[Any]]] = None

from app.metrics import ai_errors, ai_request_duration_seconds
from app.settings import (
    YANDEX_API_KEY,
    YANDEX_FOLDER_ID,
    YANDEX_INTENT_MODEL,
    YANDEX_INTENT_TIMEOUT_SECONDS,
)
from app.tracing_client import get_tracer

logger = logging.getLogger(__name__)

_client: Any = None


def _get_client() -> Any:
    global _client

    if _client is None:
        from openai import OpenAI

        _client = OpenAI(
            api_key=YANDEX_API_KEY,
            base_url="https://ai.api.cloud.yandex.net/v1",
            project=YANDEX_FOLDER_ID,
        )

    return _client


def extract_json_loose(raw: str) -> dict[str, Any] | None:
    raw = raw.strip()

    try:
        result: Any = json.loads(raw)

        if isinstance(result, dict):
            return cast(dict[str, Any], result)
    except json.JSONDecodeError:
        pass

    # На случай, если модель добавит рассуждения или пример формата
    # до реального ответа — ищем все сбалансированные {...} блоки,
    # берём последний валидный (обычно это и есть финальный ответ).
    starts = [i for i, ch in enumerate(raw) if ch == "{"]
    last_valid: dict[str, Any] | None = None

    for start in starts:
        depth = 0

        for i in range(start, len(raw)):
            if raw[i] == "{":
                depth += 1
            elif raw[i] == "}":
                depth -= 1

                if depth == 0:
                    candidate = raw[start : i + 1]

                    try:
                        result = json.loads(candidate)

                        if isinstance(result, dict):
                            last_valid = cast(dict[str, Any], result)
                    except json.JSONDecodeError:
                        pass

                    break

    return last_valid


def call_model_yandex(
    prompt: str,
    output_schema: dict[str, Any],
    schema_name: str,
    span_name: str,
    metadata: dict[str, str] | None = None,
    tags: list[str] | None = None,
    enable_thinking: bool = False,
    max_tokens: int = 256,
    timeout: int | None = None,
) -> dict[str, Any] | None:
    tracer = get_tracer()
    model_uri = f"gpt://{YANDEX_FOLDER_ID}/{YANDEX_INTENT_MODEL}/latest"
    request_timeout = timeout if timeout is not None else YANDEX_INTENT_TIMEOUT_SECONDS

    started_at = perf_counter()

    span_context = (
        tracer.start_as_current_span(span_name, openinference_span_kind="llm")
        if tracer is not None
        else nullcontext()
    )

    metadata_context: ContextManager[Any] = (
        using_metadata(metadata)
        if tracer is not None and using_metadata is not None and metadata
        else nullcontext()
    )

    tags_context: ContextManager[Any] = (
        using_tags(tags)
        if tracer is not None and using_tags is not None and tags
        else nullcontext()
    )

    with metadata_context:
        with tags_context:
            with span_context as span:
                if span is not None:
                    span.set_input(prompt)
                    span.set_attribute("llm.model_name", model_uri)

                try:
                    client = _get_client()

                    response = client.with_options(
                        timeout=request_timeout
                    ).responses.create(
                        model=model_uri,
                        temperature=0,
                        instructions="",
                        input=prompt,
                        max_output_tokens=max(max_tokens, 800),
                    )

                except Exception as error:  # noqa: BLE001 — сеть/SDK Yandex, нужен единый путь ошибки
                    ai_errors.labels(reason="yandex_request_failed").inc()
                    logger.exception("Yandex API request failed")

                    print(
                        (
                            "❌ Yandex API request failed: "
                            f"{type(error).__name__}: {error}"
                        ),
                        flush=True,
                    )

                    if span is not None:
                        span.set_output(
                            json.dumps(
                                {
                                    "error": type(error).__name__,
                                    "message": str(error),
                                },
                                ensure_ascii=False,
                            )
                        )

                    return None

                finally:
                    ai_request_duration_seconds.observe(perf_counter() - started_at)

                raw = response.output_text or ""
                data = extract_json_loose(raw)

                if data is None:
                    ai_errors.labels(reason="yandex_invalid_json").inc()
                    logger.warning("Yandex model returned invalid/empty JSON: raw=%s", raw)

                    print(
                        f"❌ Yandex model returned invalid/empty JSON (status={getattr(response, 'status', '?')})",
                        flush=True,
                    )

                    if span is not None:
                        span.set_output(
                            json.dumps({"error": "invalid_json", "raw": raw}, ensure_ascii=False)
                        )

                    return None

                if span is not None:
                    span.set_output(json.dumps(data, ensure_ascii=False))

                return data
