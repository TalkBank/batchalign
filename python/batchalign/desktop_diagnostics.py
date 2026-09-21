"""Opt-in model diagnostics without asynchronous native frame traversal."""
from contextlib import contextmanager
import os
import sys
import threading
import traceback


@contextmanager
def diagnostic_stacks(label: str, interval: float = 60):
    if os.environ.get("BATCHALIGN_DIAGNOSTIC_TRACEBACKS") != "1":
        yield
        return
    stopped = threading.Event()

    def sample():
        while not stopped.wait(interval):
            # Python holds the GIL while acquiring strong frame references.
            # A native watchdog instead walks changing frames without it.
            # If inference holds the GIL, this sampler waits; the independent
            # daemon/supervisor and CI resource sampler still remain available.
            frames = sys._current_frames()
            try:
                for identifier, frame in frames.items():
                    if identifier != threading.get_ident():
                        print(f"[desktop-stack] {label}: thread {identifier}", file=sys.stderr)
                        traceback.print_stack(frame, file=sys.stderr)
            finally:
                frames.clear()
                frame = None

    thread = threading.Thread(target=sample, name="desktop-stack-sampler", daemon=True)
    thread.start()
    try:
        yield
    finally:
        stopped.set()
        thread.join()
