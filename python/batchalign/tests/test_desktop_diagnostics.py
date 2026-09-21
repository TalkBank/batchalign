"""Exercise the real periodic sampler without loading inference models."""
import sys
import threading

from batchalign.desktop_diagnostics import diagnostic_stacks


def test_periodic_snapshots_include_caller_and_stop_on_context_exit(monkeypatch):
    import traceback

    monkeypatch.setenv("BATCHALIGN_DIAGNOSTIC_TRACEBACKS", "1")
    sampled = threading.Event()
    caller = sys._getframe()
    seen = []

    def record(frame, **kwargs):
        while frame is not None:
            if frame is caller:
                seen.append(threading.current_thread())
                sampled.set()
                return
            frame = frame.f_back

    monkeypatch.setattr(traceback, "print_stack", record)
    with diagnostic_stacks("test", interval=0.01):
        assert sampled.wait(5), "periodic sampler did not capture the caller"
    assert seen
    assert all(not thread.is_alive() for thread in seen)
