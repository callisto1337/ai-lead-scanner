from functools import lru_cache
import logging
from typing import Any, Callable, cast

from app.settings import (
    LANGFUSE_ENABLED,
    LANGFUSE_TRACING_ENVIRONMENT,
)

logger = logging.getLogger(__name__)

try:
    from langfuse import get_client as _get_client  # pyright: ignore[reportMissingImports,reportUnknownVariableType]
    get_client: Callable[[], Any] | None = cast(
        Callable[[], Any],
        _get_client,
    )
except ImportError:  # pragma: no cover - optional at runtime until installed
    get_client = None


@lru_cache(maxsize=1)
def get_langfuse_client() -> Any | None:
    if not LANGFUSE_ENABLED or get_client is None:
        return None

    # Credentials are intentionally read from env by the SDK.
    # We keep the guard above so the app still runs when Langfuse is not configured.
    try:
        client: Any = get_client()

        logger.info(
            "Langfuse tracing enabled for environment=%s",
            LANGFUSE_TRACING_ENVIRONMENT,
        )

        return client
    except Exception:
        logger.exception(
            "Langfuse client initialization failed"
        )
        return None
