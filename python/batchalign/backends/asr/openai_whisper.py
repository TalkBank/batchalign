"""OpenAI Whisper (local ``openai-whisper`` package) ASR backend.

Distinct from :class:`WhisperBackend` (HF Transformers) and
:class:`VllmAsrBackend` (HTTP). This backend uses the original
``openai/whisper`` PyPI package which supports the ``turbo`` model and
emits word-level timestamps via ``word_timestamps=True``.
"""

from __future__ import annotations

from typing import Any

from batchalign.backends.base import ASR, BatchPolicy
from batchalign.lang import LanguageCode


class OpenAIWhisperBackend(ASR):
    """Local Whisper via the ``openai-whisper`` PyPI package.

    Default model is ``"turbo"`` (the latest speed/quality preset
    shipped with openai-whisper >= 20240930). Word-level timestamps
    come from ``model.transcribe(..., word_timestamps=True)``.

    The package's `transcribe(language=...)` expects the English
    language name (`"English"`, `"Spanish"`) — same convention as HF
    Whisper. BA2 ground truth:
    `batchalign2/batchalign/pipelines/asr/oai_whisper.py:41-48`.
    """

    def __init__(
        self,
        model: str = "turbo",
        *,
        language: LanguageCode,
        device: str | None = None,
        batch_size: int = 1,
        batch_window_ms: int = 0,
    ) -> None:
        import whisper  # type: ignore[import-not-found]

        self._model = whisper.load_model(model, device=device)
        self._model_id = model
        # The runner ships `Auto` per-call; this constructor-pinned
        # name is the one the package actually receives.
        self._language = language.alpha_2 or language.name
        self._policy = BatchPolicy(max_size=batch_size, window_ms=batch_window_ms)

    @property
    def name(self) -> str:
        # v2: one AsrSegment per Whisper segment (was a single joined blob).
        return f"openai-whisper:{self._model_id}:v3"

    @property
    def batch_policy(self) -> BatchPolicy:
        return self._policy

    def call(self, batch: list[Any], *, progress: Any = None, **_kwargs: Any) -> list[Any]:
        from batchalign._core.proto import AsrInput, AsrOutput, AsrSegment, AsrWord
        import numpy as np

        outputs: list[Any] = []
        for item in batch:
            if not isinstance(item, AsrInput):
                raise TypeError(
                    f"OpenAIWhisperBackend does not handle: {type(item).__name__}"
                )
            # The media decoder already supplies PCM. A filename makes Whisper
            # launch a system ffmpeg executable, absent on clean desktops.
            audio = np.frombuffer(item.audio.pcm_f32le, dtype="<f4").copy()
            if item.audio.channels > 1:
                audio = audio.reshape(-1, item.audio.channels).mean(axis=1)
            if item.audio.sample_rate != 16000:
                import torch
                from torchaudio.functional import resample
                audio = resample(torch.from_numpy(audio), item.audio.sample_rate, 16000).numpy()
            kwargs: dict[str, Any] = {"word_timestamps": True}
            lang = self._language
            if item.language.kind == "code" and item.language.value:
                resolved = LanguageCode.from_str(item.language.value)
                lang = resolved.alpha_2 or resolved.name
            if lang:
                kwargs["language"] = lang
            result = self._model.transcribe(audio, **kwargs)

            # BA2's OAIWhisperEngine builds ONE turn per Whisper segment
            # (`for i in res["segments"]: turns.append(...)`), so each Whisper
            # segment becomes its own utterance before the CHATUtterance BERT
            # stage. Mirror that: one AsrSegment per Whisper segment, with
            # word-attached punctuation stripped (process_generation drops it)
            # so each parses as one CHAT utterance.
            segments_out: list[Any] = []
            for seg in result.get("segments", []):
                text = (seg.get("text") or "").strip()
                for _p in (".", ",", "?", "!", ";", ":", '"', "„", "“", "”", "‡", "«", "»"):
                    text = text.replace(_p, " ")
                text = " ".join(text.split())
                if not text:
                    continue
                segments_out.append(
                    AsrSegment(
                        start_ms=int((seg.get("start") or 0.0) * 1000),
                        end_ms=int((seg.get("end") or 0.0) * 1000),
                        text=text,
                        speaker=None,
                        words=[AsrWord(
                            text=word["word"].strip(),
                            start_ms=round(word["start"] * 1000),
                            end_ms=round(word["end"] * 1000),
                            confidence=word.get("probability"),
                        ) for word in seg.get("words", []) if word.get("word", "").strip()],
                    )
                )
            outputs.append(AsrOutput(source_id=item.source_id, segments=segments_out))
        return outputs


__all__ = ["OpenAIWhisperBackend"]
