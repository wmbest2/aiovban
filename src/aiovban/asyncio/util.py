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
    POP = auto()  # Pop the oldest item from the queue


@dataclass
class BackPressureQueue:
    queue_size: int
    queue_name: str = "Queue"
    back_pressure_strategy: BackPressureStrategy = field(
        default=BackPressureStrategy.DROP
    )
    _mutex: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)
    _queue: asyncio.Queue = field(default_factory=asyncio.Queue, init=False)

    def __post_init__(self):
        self._queue = asyncio.Queue(self.queue_size)

    async def put(self, packet: Any):
        if self.back_pressure_strategy in [
            BackPressureStrategy.DROP,
            BackPressureStrategy.RAISE,
        ]:
            if self.put_nowait(packet):
                return

        if self._queue.full():
            if self.back_pressure_strategy == BackPressureStrategy.DRAIN_OLDEST:
                await self._drain_queue()
            elif self.back_pressure_strategy == BackPressureStrategy.POP:
                # logger.debug(f"{self.queue_name} full. Dropping item")
                self._queue.get_nowait()

        await self._queue.put(packet)

    def put_threadsafe(self, packet: Any, loop: asyncio.AbstractEventLoop) -> None:
        """
        Thread-safe method to put an item in the queue from a background thread.
        This correctly utilizes asyncio.run_coroutine_threadsafe.
        """
        asyncio.run_coroutine_threadsafe(self.put(packet), loop)

    def put_nowait(self, packet: Any) -> bool:
        """
        Attempt to put an item in the queue without blocking.
        Returns True if successful, False if the queue is full or strategy requires blocking/draining.
        This method is strictly for same-thread operations.
        """
        if self.back_pressure_strategy in [
            BackPressureStrategy.DROP,
            BackPressureStrategy.RAISE,
        ]:
            try:
                self._queue.put_nowait(packet)
                return True
            except asyncio.QueueFull:
                if self.back_pressure_strategy == BackPressureStrategy.RAISE:
                    raise asyncio.QueueFull
                else:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f"{self.queue_name} full. Dropping item")
                    return True

        if not self._queue.full():
            self._queue.put_nowait(packet)
            return True

        if self.back_pressure_strategy == BackPressureStrategy.POP:
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
            self._queue.put_nowait(packet)
            return True

        return False

    async def _drain_queue(self):
        # Leveraging the mutex to ensure that we don't have multiple drain operations happening at the same time
        async with self._mutex:
            for i in range(int(self.queue_size / 2)):
                try:
                    self._queue.get_nowait()
                except asyncio.QueueEmpty:
                    logger.debug(f"{self.queue_name} empty")
        # logger.debug(f"Drained {int(self.queue_size / 2)} items from {self.queue_name}")

    async def get(self):
        return await self._queue.get()

    def get_nowait(self):
        return self._queue.get_nowait()
