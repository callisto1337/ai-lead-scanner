import asyncio

from app.types import MessageQueueItem


message_queue: asyncio.Queue[MessageQueueItem] = asyncio.Queue(
    maxsize=1000,
)