import json
import logging
import re
from contextlib import nullcontext
from time import perf_counter
from typing import Any, cast, ContextManager, Callable, Optional

try:
    from phoenix.otel import using_metadata, using_tags  # pyright: ignore[reportMissingImports]
except ImportError:
    using_metadata: Optional[Callable[..., ContextManager[Any]]] = None
    using_tags: Optional[Callable[..., ContextManager[Any]]] = None

import requests

from app.metrics import ai_request_duration_seconds, ai_errors
from app.tracing_client import get_tracer
from app.settings import AI_TIMEOUT_SECONDS, VLLM_API_KEY, VLLM_URL, MODEL_NAME


logger = logging.getLogger(__name__)


OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "niche_score": {
            "type": "integer",
            "minimum": 0,
            "maximum": 100,
        },
        "intent_score": {
            "type": "integer",
            "minimum": 0,
            "maximum": 100,
        },
        "description": {
            "type": "string",
        },
    },
    "required": [
        "niche_score",
        "intent_score",
        "description",
    ],
    "additionalProperties": False,
}


def extract_json(raw: str) -> dict[str, Any]:
    raw = raw.strip()

    try:
        result: Any = json.loads(raw)
    except json.JSONDecodeError:
        result = None

    if isinstance(result, dict):
        return cast(dict[str, Any], result)

    match = re.search(r"\{.*\}", raw, re.DOTALL)

    if match is None:
        raise ValueError(f"No JSON found in model response: {raw}")

    result = json.loads(match.group(0))

    if not isinstance(result, dict):
        raise ValueError("Model response is not a JSON object")

    return cast(dict[str, Any], result)


def call_model(
    prompt: str,
    metadata: dict[str, str] | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any] | None:
    tracer = get_tracer()
    payload: dict[str, Any] = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "stream": False,
        "temperature": 0,
        "max_tokens": 256,
        "chat_template_kwargs": {
            "enable_thinking": False,
        },
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "lead-classification",
                "schema": OUTPUT_SCHEMA,
            },
        },
    }

    headers = (
        {"Authorization": f"Bearer {VLLM_API_KEY}"} if VLLM_API_KEY else {}
    )

    started_at = perf_counter()

    span_context = (
        tracer.start_as_current_span(
            "model-classification",
            openinference_span_kind="llm",
        )
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
                    span.set_attribute("llm.model_name", MODEL_NAME)

                try:
                    response = requests.post(
                        f"{VLLM_URL}/chat/completions",
                        json=payload,
                        headers=headers,
                        timeout=AI_TIMEOUT_SECONDS,
                    )

                    if not response.ok:
                        ai_errors.labels(
                            reason="http_4xx" if response.status_code < 500 else "http_5xx"
                        ).inc()

                        logger.error(
                            "Model API error: status=%s body=%s",
                            response.status_code,
                            response.text,
                        )

                        print(
                            f"❌ Model API error: status={response.status_code}",
                            flush=True,
                        )
                        print(response.text, flush=True)

                        if span is not None:
                            span.set_output(
                                json.dumps(
                                    {
                                        "status": response.status_code,
                                        "body": response.text,
                                    },
                                    ensure_ascii=False,
                                )
                            )

                        return None

                    raw_result: object = response.json()

                except requests.Timeout:
                    ai_errors.labels(reason="timeout").inc()
                    logger.exception("Model API timeout")
                    print("❌ Model API timeout", flush=True)

                    if span is not None:
                        span.set_output(json.dumps({"error": "timeout"}))

                    return None

                except requests.RequestException as error:
                    ai_errors.labels(reason="connection").inc()
                    logger.exception("Model API request failed")

                    print(
                        (
                            "❌ Model API request failed: "
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

                except ValueError as error:
                    logger.exception("Model API returned non-JSON response")

                    print(
                        (
                            "❌ Model API returned non-JSON response: "
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
                    ai_request_duration_seconds.observe(
                        perf_counter() - started_at
                    )

                if not isinstance(raw_result, dict):
                    logger.warning(
                        "Model API response is not dict: %s",
                        raw_result,
                    )

                    if span is not None:
                        span.set_output(
                            json.dumps({"error": "response_is_not_dict"})
                        )

                    return None

                result = cast(dict[str, Any], raw_result)
                choices: list[Any] = result.get("choices") or []

                if not choices:
                    logger.warning("Model API returned no choices: %s", result)

                    print("❌ Model API returned no choices", flush=True)

                    if span is not None:
                        span.set_output(json.dumps({"error": "no_choices"}))

                    return None

                message: dict[str, Any] = choices[0].get("message") or {}
                raw: str = message.get("content") or ""

                try:
                    data = extract_json(raw)

                except Exception as error:
                    logger.warning("Model returned invalid JSON: raw=%s", raw)

                    print("❌ Model returned invalid JSON", flush=True)
                    print(f"error: {error}", flush=True)
                    print("raw:", flush=True)
                    print(raw, flush=True)

                    if span is not None:
                        span.set_output(
                            json.dumps(
                                {"error": str(error), "raw": raw},
                                ensure_ascii=False,
                            )
                        )

                    return None

                if span is not None:
                    span.set_output(json.dumps(data, ensure_ascii=False))

                return data