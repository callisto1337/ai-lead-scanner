from app.bootstrap import bootstrap_app
from app.lifecycle import run_monitor
from app.telegram_client import create_client
from app.handlers import register_handlers


bootstrap_app()

client = create_client()

register_handlers(client)
run_monitor(client)