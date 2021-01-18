# disable_gc
Python context manager for temporarily disabling the garbage collector.

Reentrant, threadsafe, safe for use in asyncio, and prevents GC starvation.
Safe for use inside finalizers.

# Usage
    
    from disable_gc import disable_gc
    with disable_gc:
        a = 1 # Doing things with GC disabled
    
    @disable_gc
    def func():
        a = 1  # GC disabled inside the function.
