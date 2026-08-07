from functools import lru_cache
import logging
from typing import Any

from app.settings import (
    PHOENIX_ENABLED,
    PHOENIX_PROJECT_NAME,
)

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_tracer() -> Any | None:
    if not PHOENIX_ENABLED:
        return None

    # Endpoint is read from PHOENIX_COLLECTOR_ENDPOINT by phoenix.otel.
    try:
        from phoenix.otel import register  # type: ignore[reportMissingImports]

        tracer_provider = register(project_name=PHOENIX_PROJECT_NAME)

        logger.info(
            "Phoenix tracing enabled for project=%s",
            PHOENIX_PROJECT_NAME,
        )

        return tracer_provider.get_tracer(__name__)
    except Exception:
        logger.exception("Phoenix tracer initialization failed")
        return None
