"""Lazy timing recovery for standalone desktop alignment.

The native UTR runner skips already-timed CHAT before backend dispatch. Keep
Whisper construction lazy so those files never download or load an ASR model.
"""
from __future__ import annotations

from threading import Lock
from typing import Any

from batchalign.backends.base import UTR, BatchPolicy


class DesktopTimingRecovery(UTR):
    def __init__(self, *, device: str | None = None) -> None:
        self._device = device
        self._backend: Any = None
        self._lock = Lock()

    @property
    def name(self) -> str:
        return "desktop-utr:whisper:openai/whisper-large-v3:v2"

    @property
    def batch_policy(self) -> BatchPolicy:
        return BatchPolicy(max_size=1, window_ms=0)

    def call(self, batch: list[Any], **kwargs: Any) -> list[Any]:
        if not batch:
            return []
        with self._lock:
            if self._backend is None:
                from batchalign.backends.asr.whisper import WhisperBackend
                from batchalign.lang import LanguageCode
                # UTR supplies the actual CHAT language in each AsrInput;
                # Whisper resolves that per item. English is only a fallback.
                self._backend = WhisperBackend(
                    language=LanguageCode.from_str("eng"), device=self._device,
                )
        return self._backend.call(batch, **kwargs)
