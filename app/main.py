from app.lifecycle import run_monitor
from app.telegram_client import create_client
from app.handlers import register_handlers


client = create_client()
register_handlers(client)


if __name__ == "__main__":
    run_monitor(client)
