from functools import lru_cache
import logging
from typing import Any, Callable, Optional, cast

from app.settings import (
    PHOENIX_COLLECTOR_ENDPOINT,
    PHOENIX_ENABLED,
    PHOENIX_PROJECT_NAME,
)

logger = logging.getLogger(__name__)

try:
    from phoenix.otel import register  # pyright: ignore[reportMissingImports]
    register_fn: Optional[Callable[..., Any]] = cast(Callable[..., Any], register)
except ImportError:  # pragma: no cover - optional at runtime until installed
    register_fn = None


@lru_cache(maxsize=1)
def get_tracer() -> Any | None:
    if not PHOENIX_ENABLED or register_fn is None:
        return None

    try:
        tracer_provider = register_fn(
            project_name=PHOENIX_PROJECT_NAME,
            endpoint=PHOENIX_COLLECTOR_ENDPOINT,
            protocol="http/protobuf",
            batch=True,
            auto_instrument=False,
            set_global_tracer_provider=False,
        )

        logger.info(
            "Phoenix tracing enabled: project=%s endpoint=%s",
            PHOENIX_PROJECT_NAME,
            PHOENIX_COLLECTOR_ENDPOINT,
        )

        return tracer_provider.get_tracer(__name__)
    except Exception:
        logger.exception("Phoenix tracer initialization failed")
        return None