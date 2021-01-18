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

# Notes
`disable_gc` does not and cannot monkey patch `gc.enable()`. Other threads enabling the gc in the background will leave it enabled until `disable_gc` is reentered once again.
Can be used as a reference for [bpo-31356](https://bugs.python.org/issue31356).
