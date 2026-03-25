import logging
from functools import wraps
import random
import time
from typing import Type

from core.settings import settings


def backoff(
    exception: Type[Exception] | tuple[Type[Exception]],
    max_time: int = settings.backoff_time,
    max_tries: int = 10,
    start_time: int = 1,
    factor: int = 2,
    jitter: bool = True,
    logger: logging.Logger = logging.getLogger(__name__),
):
    """Decoration function for exponential retry call inner function."""
    exceptions = exception if isinstance(exception, tuple) else (exception,)

    def func_wrapper(func):
        @wraps(func)
        def inner(*args, **kwargs):
            n = 0
            while n < max_tries:
                delay = start_time * (factor**n)
                if jitter:
                    delay += random.uniform(0.1, 1.0)
                timeout = min(delay, max_time)
                n += 1
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if timeout == max_time:
                        raise TimeoutError(f"Timeout backoff: {e}")
                    logger.warning(
                        f"{func.__name__} failed with {type(e)}. Retrying in {timeout} sec."
                    )
                    time.sleep(timeout)
            raise TimeoutError("Maximum number of attempts reached")

        return inner

    return func_wrapper
