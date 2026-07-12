import logging
import requests
from typing import Any
from app.settings import MODEL_NAME, MODEL_API_URL, AI_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)


def call_model(prompt: str) -> dict[str, Any] | None:
    payload = {
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

        result = response.json()

    except requests.Timeout:
        logger.exception("Model API timeout")

        print("❌ Model API timeout", flush=True)

        return None

    except requests.RequestException as e:
        logger.exception("Model API request failed")

        print(
            f"❌ Model API request failed: {type(e).__name__}: {e}",
            flush=True,
        )

        return None

    except ValueError as e:
        logger.exception("Model API returned non-JSON response")

        print(
            f"❌ Model API returned non-JSON response: {type(e).__name__}: {e}",
            flush=True,
        )

        return None

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

    return data
