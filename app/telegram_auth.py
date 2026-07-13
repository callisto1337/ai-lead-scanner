import argparse
import asyncio
import os
from getpass import getpass
from pathlib import Path

from telethon import TelegramClient
from telethon.errors import (
    PhoneCodeExpiredError,
    PhoneCodeInvalidError,
    PhoneNumberInvalidError,
    SessionPasswordNeededError,
)


BASE_DIR = Path(__file__).resolve().parent.parent

SESSIONS_DIR = BASE_DIR / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

SESSION_BASE = SESSIONS_DIR / "lead_monitor"


def remove_session_files() -> None:
    paths = [
        Path(f"{SESSION_BASE}.session"),
        Path(f"{SESSION_BASE}.session-journal"),
        Path(f"{SESSION_BASE}.session-shm"),
        Path(f"{SESSION_BASE}.session-wal"),
    ]

    removed = False

    for path in paths:
        if path.exists():
            path.unlink()
            print(f"Удалён файл: {path}", flush=True)
            removed = True

    if not removed:
        print("Старая сессия не найдена", flush=True)


async def authorize(reset: bool) -> None:
    api_id_raw = os.getenv("API_ID")
    api_hash = os.getenv("API_HASH")

    if not api_id_raw:
        raise RuntimeError("Не указан API_ID")

    if not api_hash:
        raise RuntimeError("Не указан API_HASH")

    api_id = int(api_id_raw)

    if reset:
        remove_session_files()

    client = TelegramClient(
        str(SESSION_BASE),
        api_id,
        api_hash,
    )

    await client.connect()

    try:
        if await client.is_user_authorized():
            me = await client.get_me()

            print(
                "Сессия уже авторизована:",
                getattr(me, "phone", None)
                or getattr(me, "username", None)
                or getattr(me, "id", None),
                flush=True,
            )
            return

        phone = input(
            "Введите номер телефона в международном формате, например +79991234567: "
        ).strip()

        sent_code = await client.send_code_request(phone)

        code = input(
            "Введите код из Telegram: "
        ).strip().replace(" ", "")

        try:
            await client.sign_in(
                phone=phone,
                code=code,
                phone_code_hash=sent_code.phone_code_hash,
            )

        except SessionPasswordNeededError:
            password = getpass(
                "Введите пароль двухэтапной аутентификации: "
            )

            await client.sign_in(
                password=password,
            )

        me = await client.get_me()

        print("", flush=True)
        print("Авторизация выполнена", flush=True)
        print(
            "Аккаунт:",
            getattr(me, "phone", None)
            or getattr(me, "username", None)
            or getattr(me, "id", None),
            flush=True,
        )
        print(
            f"Сессия сохранена: {SESSION_BASE}.session",
            flush=True,
        )

    except (
        PhoneCodeInvalidError,
        PhoneCodeExpiredError,
        PhoneNumberInvalidError,
    ) as error:
        raise RuntimeError(
            f"Ошибка авторизации Telegram: {type(error).__name__}"
        ) from error

    finally:
        await client.disconnect()


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--reset",
        action="store_true",
        help="Удалить существующую сессию перед авторизацией",
    )

    args = parser.parse_args()

    asyncio.run(
        authorize(
            reset=args.reset,
        )
    )


if __name__ == "__main__":
    main()