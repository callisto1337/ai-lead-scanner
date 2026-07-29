import json
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace
from typing import cast, Any

from app.db.messages import save_message
from app.queue import message_queue
from app.types import MessageQueueItem, TgUserId, TgChatId, TgMessageId, NewMessageEvent, MessageData


async def run_load_test() -> None:
    started_at = perf_counter()

    path = (
            Path(__file__).resolve().parent.parent
            / "reports"
            / "load_test_messages.json"
    )

    rows = json.loads(
        path.read_text(encoding="utf-8")
    )

    for index, row in enumerate(rows, start=1):
        created_at = datetime.now(timezone.utc)

        user_id = (
            TgUserId(row["user_id"])
        )

        message_data: MessageData = {
            "text": row["text"],
            "user_id": user_id,
            "user_link": None,
            "link": None,
            "tg_created_at": created_at,
        }

        test_event = cast(
            NewMessageEvent,
            cast(
                Any,
                SimpleNamespace(
                    chat_id=TgChatId(0),
                    message=SimpleNamespace(
                        id=TgMessageId(index),
                        reply_to_msg_id=None,
                        reply_to=None,
                        text=row["text"],
                        date=created_at,
                        post=False,
                    ),
                ),
            ),
        )

        message_id = save_message(
            data=message_data,
            event=test_event,
        )

        job: MessageQueueItem = {
            "message_id": message_id,
            "tg_chat_id": TgChatId(0),
            "tg_message_id": TgMessageId(index),
            "reply_tg_message_id": None,

            "clean_text": row["text"],
            "sender_id": user_id,
            "sender_name": None,
            "sender_username": None,
            "sender": None,

            "reply_text": None,
            "reply_sender_id": None,

            "source_link": "https://t.me/test",
            "source_title": "Load test",
            "created_at": created_at,
            "enqueued_at": datetime.now(timezone.utc),
        }

        await message_queue.put(job)

    print(
        f"🧪 Добавлено тестовых сообщений: {len(rows)}",
        flush=True,
    )

    await message_queue.join()

    duration_seconds = perf_counter() - started_at

    print(
        (
            "✅ Нагрузочный тест завершён: "
            f"messages={len(rows)}, "
            f"duration={duration_seconds:.2f}s, "
            f"throughput={len(rows) / duration_seconds:.2f} msg/s"
        ),
        flush=True,
    )
