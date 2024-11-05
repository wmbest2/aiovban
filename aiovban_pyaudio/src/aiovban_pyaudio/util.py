import asyncio
import functools
import threading


def run_on_background_thread(func):
    def run_loop(loop, future, *args, **kwargs):
        asyncio.set_event_loop(loop)
        loop.run_until_complete(func(*args, **kwargs))
        future.set_result(None)

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()
        future = asyncio.get_running_loop().create_future()
        thread = threading.Thread(
            target=run_loop, args=(loop, future, *args), kwargs=kwargs, daemon=True
        )
        thread.start()
        future.add_done_callback(lambda s: thread.join(timeout=1))
        return future

    return wrapper
