import gc
from disable_gc import disable_gc
import threading
from unittest import TestCase
from concurrent.futures import ThreadPoolExecutor

# For multithread tests
THREADCOUNT = 8


def _gen(n):
    """Return gen-n counter"""
    return gc.get_count()[n]


class TestDisableGC(TestCase):
    @classmethod
    def setUpClass(cls):
        # These tests are built for a specific threshold.
        assert gc.get_threshold() == (700, 10, 10)
        super().setUpClass()

    def setUp(self):
        # Make sure GC is running before every test.
        super().setUp()
        self.en()

    def tearDown(self):
        # Make sure GC is running after every test.
        self.en()
        super().tearDown()

    def assert_enabled(self):
        self.assertTrue(gc.isenabled())

    en = assert_enabled

    def assert_disabled(self):
        self.assertFalse(gc.isenabled())

    dis = assert_disabled

    def test_sanity(self):
        """Makes sure a single disable gc works."""
        with disable_gc:
            self.dis()
        self.en()

    def test_reentrancy(self):
        """Multiple disable_gc one inside the other"""
        with disable_gc:
            self.dis()
            with disable_gc:
                self.dis()
            self.dis()
        self.en()

    def test_finalizer(self):
        """Disable GC inside a finalizer"""
        finalizer_ran = False

        class A:
            def __del__(self_):
                nonlocal finalizer_ran
                with disable_gc:
                    self.dis()
                finalizer_ran = True

        a = A()
        with disable_gc:
            del a
            self.assertTrue(finalizer_ran)

        self.en()

    def test_multithread(self):
        b = threading.Barrier(THREADCOUNT)

        def disable():
            thread_id = b.wait()
            # All running at once with lots of disable __enter__ and __exit__.
            with disable_gc:
                self.dis()
                # Finish with 1 thread inside the disable.
                if thread_id == 0:
                    b.wait()
                    # Make sure it's still disabled.
                    self.dis()

            if thread_id != 0:
                b.wait()
            else:
                # Last thread checks if it's enabled
                self.en()

            # All drain at once except 1
            b.wait()
            with disable_gc:
                b.wait()
                if thread_id == 0:
                    b.wait()
                    self.dis()
                    return

            # Make sure it's disabled when all were concurrently
            # enabling except 1.
            self.dis()
            b.wait()

        with ThreadPoolExecutor(THREADCOUNT) as executor:
            for i in range(THREADCOUNT):
                executor.submit(disable)

        self.en()

    def test_background_enable(self):
        """gc is enabled in the background

        This is an unwanted behavior we can't control as GC is globaL.
        """
        with disable_gc:
            gc.enable()
            self.en()
            with disable_gc:
                self.dis()
            self.dis()
        self.en()

    def test_collection(self):
        """Make sure gen0 is cleared if above threshold on __enter__

        Periodic clear is important to keep RAM usage sane.
        """
        gc.collect(0)
        allocated = [[] for i in range(130)]  # noqa

        self.assertGreater(_gen(0), 100)
        with disable_gc:
            # Collection didn't happen
            self.assertGreater(_gen(0), 100)
            allocated2 = [[] for i in range(600)]  # noqa
            self.assertGreater(_gen(0), 700)  # gen0 collection should occur.

            with disable_gc:
                # Collection occurred.
                self.assertLess(_gen(0), 10)

    def test_starvation(self):
        """GC isn't starvated, and gen1 collection periodically runs"""
        gc.collect()
        with disable_gc:
            # Trigger 10 consecutive manual colllections without
            # releasing GC.
            for i in range(10):
                gc.collect(0)

            allocated = [[] for i in range(700)]  # noqa

            # Starvation didn't kick in
            with disable_gc:
                self.assertEqual(_gen(1), 11)

            allocated2 = [[] for i in range(700)]  # noqa
            self.assertEqual(_gen(1), 11)
            with disable_gc:
                # Anti-starvation enabled.
                self.assertEqual(_gen(1), 0)
