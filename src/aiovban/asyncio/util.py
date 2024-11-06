import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

logger = logging.getLogger(__package__ + "." + __name__)


class BackPressureStrategy(Enum):

    DROP = auto()  # Drop packets when queue is full
    DRAIN_OLDEST = auto()  # Drain oldest packets until queue is half full
    BLOCK = auto()  # Block until there is space in the queue
    RAISE = auto()  # Raise an exception when queue is full
    POP = auto() # Pop the oldest item from the queue


@dataclass
class BackPressureQueue:
    queue_size: int
    queue_name: str = "Queue"
    back_pressure_strategy: BackPressureStrategy = field(
        default=BackPressureStrategy.DROP
    )
    _mutex: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)
    _queue: asyncio.Queue = field(default_factory=asyncio.Queue, init=False)
    _loop: asyncio.AbstractEventLoop = field(default=None, init=False)

    def __post_init__(self):
        self._queue = asyncio.Queue(self.queue_size)
        self._loop = asyncio.get_event_loop()

    async def put(self, packet: Any):
        if self.back_pressure_strategy in [
            BackPressureStrategy.DROP,
            BackPressureStrategy.RAISE,
        ]:
            try:
                self._queue.put_nowait(packet)
                return
            except asyncio.QueueFull:
                if self.back_pressure_strategy == BackPressureStrategy.RAISE:
                    raise asyncio.QueueFull
                else:
                    logger.debug(f"{self.queue_name} full. Dropping item")
                    return

        if self._queue.full():
            if self.back_pressure_strategy == BackPressureStrategy.DRAIN_OLDEST:
                await self._drain_queue()
            elif self.back_pressure_strategy == BackPressureStrategy.POP:
                #logger.debug(f"{self.queue_name} full. Dropping item")
                self._queue.get_nowait()

        await self._queue.put(packet)

    async def _drain_queue(self):
        # Leveraging the mutex to ensure that we don't have multiple drain operations happening at the same time
        async with self._mutex:
            for i in range(int(self.queue_size / 2)):
                try:
                    self._queue.get_nowait()
                except asyncio.QueueEmpty:
                    print(f"{self.queue_name} empty")
        logger.debug(f"Drained {int(self.queue_size / 2)} items from {self.queue_name}")

    async def get(self):
        return await self._queue.get()

    def get_nowait(self):
        return self._queue.get_nowait()
