"""PhoneticXeus inference with word ownership projected through phone DP."""

from __future__ import annotations

import hashlib
import json
import logging
import threading
from typing import Any, Mapping

from batchalign.backends.base import BatchPolicy, Phonetic
from .utils.inference import group_utterances, transcribe_batch
from .utils.pronunciation import Pronunciations
from .utils.projection import UNRESOLVED, project_phones

logger = logging.getLogger(__name__)

MODEL = "changelinglab/PhoneticXeus"
REVISION = "3a8d860fa68f8936ceb4196651221215bab9dae4"


class PhoneticXeusBackend(Phonetic):
    """Observed IPA from audio; reference pronunciations determine grouping only."""

    def __init__(
        self,
        *,
        model: str = MODEL,
        revision: str = REVISION,
        device: str | None = None,
        pronunciations: Mapping[str, str] | None = None,
        batch_size: int | None = None,
    ):
        if len(revision) != 40 or any(ch not in "0123456789abcdef" for ch in revision):
            raise ValueError(
                "PhoneticXeus revision must be an immutable 40-character commit SHA"
            )
        if batch_size is not None and batch_size < 1:
            raise ValueError("batch_size must be positive")
        self.batch_size = batch_size
        self.model_id, self.revision, self.device = model, revision, device
        self.pronunciations = Pronunciations(pronunciations)
        # Textual replaces stderr with a stream whose fileno() is -1. Hugging
        # Face's first progress bar creates a multiprocessing resource tracker,
        # which cannot inherit that descriptor. Initialize its lock here, before
        # the dashboard starts and inference moves to an engine worker thread.
        from huggingface_hub.utils import tqdm

        tqdm.get_lock()
        self._model = None
        self._lock = threading.Lock()

    @property
    def name(self) -> str:
        overrides = json.dumps(
            self.pronunciations.overrides, sort_keys=True, ensure_ascii=False
        )
        digest = hashlib.sha256(overrides.encode()).hexdigest()
        return f"phoneticxeus:{self.model_id}:{self.revision}:{self.pronunciations.version}:{digest}:{self.device}:{self.batch_size}:v6"

    @property
    def batch_policy(self) -> BatchPolicy:
        return BatchPolicy.one()

    def call(
        self, batch: list[Any], *, progress: Any = None, **_kwargs: Any
    ) -> list[Any]:
        import numpy as np
        import torch
        import torchaudio.functional as audio_ops
        from huggingface_hub import snapshot_download
        from transformers import AutoModel
        from batchalign._core.proto import PhoneticOutput, PhoneticResult

        outputs = []
        device = self.device or ("cuda" if torch.cuda.is_available() else "cpu")
        batch_size = self.batch_size or (2 if str(device).startswith("cuda") else 1)
        with self._lock:
            for item in batch:
                sample_rate = int(item.audio.sample_rate)
                if sample_rate <= 0:
                    raise ValueError(
                        "PhoneticXeus requires a positive audio sample rate"
                    )
                waveform = np.frombuffer(item.audio.pcm_f32le, dtype="<f4")
                results = [
                    PhoneticResult(
                        index=utterance.index,
                        ipa=[unit.text if unit.pause else UNRESOLVED for unit in utterance.units],
                    )
                    for utterance in item.utterances
                ]
                for utterance in item.utterances:
                    start = utterance.start_ms * sample_rate // 1000
                    end = utterance.end_ms * sample_rate // 1000
                    if not 0 <= start < end <= len(waveform):
                        raise ValueError(f"Utterance {utterance.index} is outside the audio")

                # Keep original utterance/unit ownership through grouping and
                # length sorting; the output CHAT order never changes.
                groups = group_utterances(item.utterances)
                jobs = []
                for group in groups:
                    owners = [
                        (u, w) for u in group
                        for w, unit in enumerate(item.utterances[u].units)
                        if not unit.pause
                    ]
                    if owners:
                        start = item.utterances[group[0]].start_ms
                        end = item.utterances[group[-1]].end_ms
                        jobs.append((start, end, owners))
                jobs.sort(key=lambda job: job[1] - job[0])
                if jobs and self._model is None:
                    # A local snapshot pins the wrapper's internal pxeus import.
                    path = snapshot_download(
                        self.model_id, revision=self.revision,
                        allow_patterns=["*.json", "*.py", "model.safetensors", "pxeus/**"],
                    )
                    self._model = AutoModel.from_pretrained(path, trust_remote_code=True).to(device).eval()
                for offset in range(0, len(jobs), batch_size):
                    current = jobs[offset:offset + batch_size]
                    audio_batch, references = [], []
                    for start, end, owners in current:
                        audio = torch.from_numpy(waveform[
                            start * sample_rate // 1000:end * sample_rate // 1000
                        ].copy())
                        if sample_rate != 16000:
                            audio = audio_ops.resample(audio, sample_rate, 16000)
                        audio_batch.append(audio)
                        references.append([
                            self.pronunciations(item.utterances[u].units[w].text, item.language)
                            for u, w in owners
                        ])
                    phone_batch = transcribe_batch(self._model, audio_batch)
                    if len(phone_batch) != len(current):
                        raise ValueError("PhoneticXeus returned the wrong number of windows")
                    for (_, _, owners), phones, reference in zip(current, phone_batch, references):
                        for (u, w), value in zip(owners, project_phones(phones, reference)):
                            results[u].ipa[w] = value
                    if progress:
                        progress(min(offset + batch_size, len(jobs)), len(jobs))
                for utterance, result in zip(item.utterances, results):
                    unresolved = [
                        unit.text for unit, value in zip(utterance.units, result.ipa)
                        if not unit.pause and value == UNRESOLVED
                    ]
                    if unresolved:
                        logger.warning(
                            "%s: phonetic %s–%s ms: no phones aligned to %r; marked %s on %%pho",
                            item.source_id, utterance.start_ms, utterance.end_ms,
                            unresolved, UNRESOLVED,
                        )
                outputs.append(
                    PhoneticOutput(source_id=item.source_id, utterances=results)
                )
        return outputs
