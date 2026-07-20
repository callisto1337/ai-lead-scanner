from typing import cast

from app.bootstrap import bootstrap_app
from app.lifecycle import run_monitor
from app.telegram_client import create_client
from app.handlers import register_handlers
from app.types import TelegramClientProtocol

bootstrap_app()

client = create_client()

register_handlers(
    cast(TelegramClientProtocol, cast(object, client)),
)
run_monitor(
    cast(TelegramClientProtocol, cast(object, client)),
)