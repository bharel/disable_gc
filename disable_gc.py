from contextlib import (ContextDecorator as _ContextDecorator,
                        AbstractContextManager as _AbstractContextManager)
from threading import RLock as _RLock
import gc as _gc

__author__ = "Bar Harel"
__version__ = "0.1.0"
__license__ = "MIT License"
__all__ = ["disable_gc"]


_gen0_collection_threshold, _gen1_collection_threshold, _ = _gc.get_threshold()


class _GC(_ContextDecorator, _AbstractContextManager):
    """Reentrant contextmanager for disabling and enabling GC.

    Threadsafe, safe for use in asyncio, and prevents GC starvation.
    Safe for use inside finalizers.

    Example usage:

        >>> with disable_gc:
        ...     a = 1  # Doing things with GC disabled

    Can be used as a decorator as well:

        >>> @disable_gc
        ... def func():
        ...     a = 1  # GC disabled inside the function.


    """

    def __init__(self):
        self._lock = _RLock()  # RLock is a must for finalizer use.
        self._counter = 0

    # Order is important throughout the function if GC reenters it.
    def __enter__(self, *, _gc=_gc, _getcount=_gc.get_count):
        with self._lock:
            self._counter += 1

            # Disable if enabled (maybe from outside threads), otherwise no-op.
            _gc.disable()

            gen0, gen1, _ = _getcount()

            # Collect gen0 once per entry if needed.
            if gen0 > _gen0_collection_threshold:
                # Prevent GC starvation (gen1, gen2, internal LL cleanup).
                # Acts globally so do it sparingly according to gen1 threshold.
                if gen1 > _gen1_collection_threshold:
                    # Force GC collecion.
                    _gc.enable()
                    (lambda: None)()  # Run GC.
                    _gc.disable()
                else:
                    _gc.collect(0)

        return super().__enter__()

    # Order is important throughout the function if GC reenters it.
    def __exit__(self, exc_type, exc_value, traceback):
        with self._lock:
            self._counter -= 1
            if self._counter == 0:
                _gc.enable()
        return super().__exit__(exc_type, exc_value, traceback)


disable_gc = _GC()
