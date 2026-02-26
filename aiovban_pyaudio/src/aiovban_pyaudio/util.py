import asyncio
import functools
import threading


def run_on_background_thread(func):
    def run_loop(loop, future, origin_loop, *args, **kwargs):
        try:
            asyncio.set_event_loop(loop)
            kwargs["origin_loop"] = origin_loop
            loop.run_until_complete(func(*args, **kwargs))
        except Exception as e:
            if not future.done():
                origin_loop.call_soon_threadsafe(future.set_exception, e)
        finally:
            loop.stop()
            loop.close()
            if not future.done():
                origin_loop.call_soon_threadsafe(future.set_result, None)

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()
        origin_loop = asyncio.get_running_loop()
        future = asyncio.get_running_loop().create_future()
        thread = threading.Thread(
            target=run_loop,
            args=(loop, future, origin_loop, *args),
            kwargs=kwargs,
            daemon=True,
        )
        thread.start()
        future.add_done_callback(lambda s: thread.join(timeout=1))
        return future

    return wrapper


class FrameBuffer:
    """
    A utility class to manage a buffer of audio frames. This class is used to store audio frames
    with a maximum frame count. When the buffer is full, the oldest frames are dropped to make
    room for new frames and keep latency low.

    Methods:
        __init__(max_frame_count: int, bytes_per_frame: int = 4):
            Initializes the FrameBuffer with a maximum frame count and bytes per frame.

        write(data: bytes, frames: int):
            Writes data to the buffer and updates the frame count. Thread-safe.

        size():
            Returns the current size of the buffer in bytes and the frame count. Thread-safe.

        read(num_frames: int):
            Reads a specified number of frames from the buffer, dropping the oldest frames if necessary. Thread-safe.

        synchronize(bytes_per_frame: int):
            Resets the buffer and updates the bytes per frame. Thread-safe.
    """

    def __init__(self, max_frame_count: int, bytes_per_frame: int = 1):
        """
        Initializes the FrameBuffer with a maximum frame count and bytes per frame.

        Args:
            max_frame_count (int): The maximum number of frames the buffer can hold.
            bytes_per_frame (int): The number of bytes per frame. Default is 4.
        """
        self._buffer = b""
        self._frame_count = 0
        self._max_frame_count = max_frame_count
        self._bytes_per_frame = bytes_per_frame
        self._mutex = threading.Lock()

    def write(self, data: bytes, frames: int):
        """
        Writes data to the buffer and updates the frame count.

        Args:
            data (bytes): The audio data to write to the buffer.
            frames (int): The number of frames in the data.
        """
        with self._mutex:
            self._buffer += data
            self._frame_count += frames

    def size(self):
        """
        Returns the current size of the buffer in bytes and the frame count.

        Returns:
            tuple: A tuple containing the size of the buffer in bytes and the frame count.
        """
        with self._mutex:
            return len(self._buffer), self._frame_count

    def read(self, num_frames: int, drop_frames=True):
        """
        Reads a specified number of frames from the buffer, dropping the oldest frames if necessary.

        Args:
            num_frames (int): The number of frames to read from the buffer.
            drop_frames (bool): Whether to drop frames if the buffer is full. Default is True.

        Returns:
            tuple: A tuple containing the read data, the number of frames read, and the number of frames dropped.
        """
        with self._mutex:
            maximum_available_frames = min(num_frames, self._frame_count)
            bytes_for_frames = self._bytes_per_frame * maximum_available_frames

            if drop_frames:
                excess_frames = max(0, self._frame_count - self._max_frame_count)
                bytes_to_drop = self._bytes_per_frame * excess_frames
            else:
                excess_frames = 0
                bytes_to_drop = 0

            buffer_data = self._buffer[bytes_to_drop : bytes_to_drop + bytes_for_frames]
            self._buffer = self._buffer[bytes_to_drop + bytes_for_frames :]
            self._frame_count = max(
                0, self._frame_count - maximum_available_frames - excess_frames
            )

            return buffer_data, maximum_available_frames, excess_frames

    def synchronize(self, bytes_per_frame: int):
        """
        Resets the buffer and updates the bytes per frame.

        Args:
            bytes_per_frame (int): The new number of bytes per frame.
        """
        with self._mutex:
            self._buffer = b""
            self._frame_count = 0
            self._bytes_per_frame = bytes_per_frame
