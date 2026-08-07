import json
import logging
from contextlib import nullcontext
from time import perf_counter
from typing import Any, cast, ContextManager, Callable, Optional

try:
    from phoenix.otel import using_metadata, using_tags  # pyright: ignore[reportMissingImports]
except ImportError:
    using_metadata: Optional[Callable[..., ContextManager[Any]]] = None
    using_tags: Optional[Callable[..., ContextManager[Any]]] = None

import requests

from app.metrics import ai_request_duration_seconds
from app.tracing_client import get_tracer
from app.settings import AI_TIMEOUT_SECONDS, MODEL_API_URL, MODEL_NAME


logger = logging.getLogger(__name__)


def call_model(
    prompt: str,
    metadata: dict[str, str] | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any] | None:
    tracer = get_tracer()
    payload: dict[str, Any] = {
        "prompt": prompt,
        "model": MODEL_NAME,
        "format": "json",
        "stream": False,
        "think": False,
        "options": {
            "temperature": 0,
            "num_predict": 256,
        },
    }

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
                        f"{MODEL_API_URL}/generate",
                        json=payload,
                        timeout=AI_TIMEOUT_SECONDS,
                    )

                    if not response.ok:
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
                    logger.exception("Model API timeout")
                    print("❌ Model API timeout", flush=True)

                    if span is not None:
                        span.set_output(json.dumps({"error": "timeout"}))

                    return None

                except requests.RequestException as error:
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

                if not result.get("ok"):
                    error = result.get("error")
                    raw = result.get("raw")

                    logger.warning(
                        "Model returned invalid JSON: error=%s raw=%s",
                        error,
                        raw,
                    )

                    print("❌ Model returned invalid JSON", flush=True)
                    print(f"error: {error}", flush=True)
                    print("raw:", flush=True)
                    print(raw, flush=True)

                    if span is not None:
                        span.set_output(
                            json.dumps(
                                {"error": error, "raw": raw},
                                ensure_ascii=False,
                            )
                        )

                    return None

                data = result.get("data")

                if not isinstance(data, dict):
                    logger.warning("Model API data is not dict: %s", result)

                    print("❌ Model API data is not dict", flush=True)
                    print("result:", flush=True)
                    print(result, flush=True)

                    if span is not None:
                        span.set_output(json.dumps({"error": "data_is_not_dict"}))

                    return None

                if span is not None:
                    span.set_output(json.dumps(data, ensure_ascii=False))

                return cast(dict[str, Any], data)