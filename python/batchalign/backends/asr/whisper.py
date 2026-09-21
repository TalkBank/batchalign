"""WhisperBackend: local Whisper ASR via HuggingFace ``transformers``.

The default model is ``openai/whisper-large-v3``, matching BA2's
choice (``batchalign2/batchalign/pipelines/asr/whisper.py``). The
dependency on ``transformers``/``torch`` is lazy — constructing a
:class:`WhisperBackend` is free until ``__init__`` actually imports
the libraries.

Whisper provides word-level timestamps via the HF pipeline's
``return_timestamps="word"`` option, which is what we want for the
``AsrSegment.words`` field. Forced alignment is **not** done here —
use :class:`Wav2Vec2FaBackend` from :mod:`batchalign.backends.wav2vec2`
or :class:`WhisperXBackend` for that.
"""

from __future__ import annotations

import math
from typing import Any

from batchalign.backends.base import ASR, UTR, BatchPolicy
from batchalign.lang import LanguageCode


def _monotonic_boundaries(boundaries: list[int]) -> list[int]:
    """Least-squares nondecreasing fit, without reordering spoken words.

    Whisper's overlapping audio chunks can produce a word starting before
    the preceding word ends. Pool adjacent violations so both estimates
    share the correction instead of pushing every later word forward.
    Already ordered timestamps are unchanged. This is local to Whisper's
    single word sequence; concurrent speakers in other ASR providers are
    deliberately not flattened.
    """
    blocks: list[tuple[int, int]] = []
    for value in boundaries:
        total, count = value, 1
        while blocks and blocks[-1][0] * count > total * blocks[-1][1]:
            previous, size = blocks.pop()
            total += previous
            count += size
        blocks.append((total, count))
    return [
        (total + count // 2) // count
        for total, count in blocks for _ in range(count)
    ]


class WhisperBackend(ASR, UTR):
    """Local Whisper ASR backend; also serves `Task.Utr`.

    HF Whisper's `generate_kwargs["language"]` accepts the English
    language name (`"English"`, `"Spanish"`) — that's what
    pycountry's `.name` gives us. BA2 ground truth:
    `batchalign2/batchalign/pipelines/asr/whisper.py:36-45`.
    """

    def __init__(
        self,
        model: str = "openai/whisper-large-v3",
        *,
        language: LanguageCode,
        batch_size: int = 32,
        batch_window_ms: int = 50,
        device: str | None = None,
        chunk_length_s: int = 15,
    ) -> None:
        from transformers import pipeline  # type: ignore[import-not-found]
        import torch

        from batchalign.backends.asr._torch_audio import disable_torchcodec

        disable_torchcodec()
        # Match the CLI's explicit MPS opt-in policy. HF's ambient default
        # otherwise silently selects MPS even without --allow-mps.
        device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        kwargs: dict[str, Any] = {"chunk_length_s": chunk_length_s, "device": device}
        cpu = torch.device(device).type == "cpu"
        if cpu:
            # The checkpoint's auto dtype is float16. Intel macOS is pinned
            # to torch 2.2, whose CPU LayerNorm has no half-precision kernel.
            # Choose the dtype while loading to avoid a second model copy.
            kwargs["dtype"] = torch.float32
        self._pipe = pipeline(
            "automatic-speech-recognition",
            model=model,
            **kwargs,
        )
        self._model = model
        # HF Whisper wants the English language name in its
        # `generate_kwargs["language"]`. The runner always ships `Auto`
        # at call time, so this constructor-pinned value is what
        # actually reaches the model.
        self._language = language.name
        self._policy = BatchPolicy(max_size=batch_size, window_ms=batch_window_ms)

    @property
    def name(self) -> str:
        # Auto-language inputs still use the constructor's language hint.
        return f"whisper:{self._model}:{self._language}:v3"

    @property
    def batch_policy(self) -> BatchPolicy:
        return self._policy

    def call(self, batch: list[Any], *, progress: Any = None, **_kwargs: Any) -> list[Any]:
        from batchalign._core.proto import AsrInput, AsrOutput

        outputs: list[Any] = []
        for item in batch:
            if not isinstance(item, AsrInput):
                raise TypeError(
                    f"WhisperBackend does not handle input type: {type(item).__name__}"
                )
            outputs.append(self._transcribe(item, AsrOutput))
        return outputs

    # ----- internals -----------------------------------------------------

    def _transcribe(self, item: Any, AsrOutput: type) -> Any:
        import numpy as np  # type: ignore[import-not-found]
        from batchalign._core.proto import AsrSegment, AsrWord

        wave = np.frombuffer(item.audio.pcm_f32le, dtype=np.float32)
        # HF Whisper expects the English name ("english", "spanish", …),
        # not the ISO alpha_3 code ("eng", "spa", …). The wire payload
        # ships `LanguageSpec::Code(alpha_3)` (e.g. from the UTR runner
        # reading `@Languages: eng`), so we resolve it back through
        # `LanguageCode` to get the English name. `self._language` is
        # already the English name from the constructor.
        if item.language.kind == "code":
            try:
                language: str | None = LanguageCode.from_str(item.language.value).name
            except ValueError:
                language = self._language
        else:
            language = self._language
        gen_kwargs: dict[str, Any] = {"task": "transcribe"}
        if language is not None:
            gen_kwargs["language"] = language

        result = self._pipe(
            {"array": wave, "sampling_rate": item.audio.sample_rate},
            return_timestamps="word",
            generate_kwargs=gen_kwargs or None,
        )

        # HF returns
        #   {"text": "...", "chunks": [{"timestamp": (s, e), "text": "..."}, ...]}
        # Keep the ordered words in one segment. Native post-processing
        # recovers utterances from its text and word boundaries.
        chunks = result.get("chunks", [])
        duration_ms = round(len(wave) * 1000 / item.audio.sample_rate)
        boundaries: list[int] = []
        for index, chunk in enumerate(chunks):
            ts = chunk.get("timestamp") or (None, None)
            start_s = ts[0] if ts[0] is not None else (
                boundaries[-1] / 1000 if boundaries else 0
            )
            end_s = ts[1] if ts[1] is not None else (
                duration_ms / 1000 if index == len(chunks) - 1 else start_s
            )
            if not math.isfinite(start_s) or not math.isfinite(end_s):
                raise ValueError("Whisper returned a non-finite word timestamp")
            boundaries.extend(
                max(0, min(duration_ms, round(value * 1000)))
                for value in (start_s, end_s)
            )
        boundaries = _monotonic_boundaries(boundaries)
        words: list[Any] = []
        for index, chunk in enumerate(chunks):
            words.append(
                AsrWord(
                    text=(chunk.get("text") or "").strip(),
                    start_ms=boundaries[2 * index],
                    end_ms=boundaries[2 * index + 1],
                    confidence=None,
                )
            )

        if not words:
            return AsrOutput(source_id=item.source_id, segments=[])

        full_text = (result.get("text") or " ".join(w.text for w in words)).strip()
        segment = AsrSegment(
            start_ms=words[0].start_ms,
            end_ms=words[-1].end_ms,
            text=full_text,
            speaker=None,
            words=words,
        )
        return AsrOutput(source_id=item.source_id, segments=[segment])


__all__ = ["WhisperBackend"]
