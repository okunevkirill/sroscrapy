from time import perf_counter
from functools import wraps


def timer(func):
    """Decorator for getting the running time of a function"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        start_timer = perf_counter()
        return_value = func(*args, **kwargs)
        stop_timer = perf_counter()
        print(f"[*] - Время работы '{func.__name__}': {stop_timer - start_timer}")
        return return_value

    return wrapper
