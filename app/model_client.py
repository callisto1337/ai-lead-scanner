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
        "temperature": 0,
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
            return None

        result = response.json()

    except requests.Timeout:
        logger.exception("Model API timeout")
        return None

    except requests.RequestException:
        logger.exception("Model API request failed")
        return None

    except ValueError:
        logger.exception("Model API returned non-JSON response")
        return None

    if not result.get("ok"):
        logger.warning(
            "Model returned invalid JSON: error=%s raw=%s",
            result.get("error"),
            result.get("raw"),
        )
        return None

    data = result.get("data")

    if not isinstance(data, dict):
        logger.warning("Model API data is not dict: %s", result)
        return None

    return data
