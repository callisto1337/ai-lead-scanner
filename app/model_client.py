import logging
from time import perf_counter
from typing import Any, cast

import requests

from app.metrics import ai_request_duration_seconds
from app.settings import AI_TIMEOUT_SECONDS, MODEL_API_URL, MODEL_NAME


logger = logging.getLogger(__name__)


def call_model(prompt: str) -> dict[str, Any] | None:
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

            return None

        raw_result: object = response.json()

    except requests.Timeout:
        logger.exception("Model API timeout")
        print("❌ Model API timeout", flush=True)
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

        return None

    data = result.get("data")

    if not isinstance(data, dict):
        logger.warning("Model API data is not dict: %s", result)

        print("❌ Model API data is not dict", flush=True)
        print("result:", flush=True)
        print(result, flush=True)

        return None

    return cast(dict[str, Any], data)