"""PhoneticXeus inference with word ownership projected through phone DP."""

from __future__ import annotations

import hashlib
import json
import threading
from typing import Any, Mapping

from batchalign.backends.base import BatchPolicy, Phonetic
from .utils.pronunciation import Pronunciations
from .utils.projection import project_phones

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
    ):
        if len(revision) != 40 or any(ch not in "0123456789abcdef" for ch in revision):
            raise ValueError(
                "PhoneticXeus revision must be an immutable 40-character commit SHA"
            )
        self.model_id, self.revision, self.device = model, revision, device
        self.pronunciations = Pronunciations(pronunciations)
        self._model = None
        self._lock = threading.Lock()

    @property
    def name(self) -> str:
        overrides = json.dumps(
            self.pronunciations.overrides, sort_keys=True, ensure_ascii=False
        )
        digest = hashlib.sha256(overrides.encode()).hexdigest()
        return f"phoneticxeus:{self.model_id}:{self.revision}:{self.pronunciations.version}:{digest}:{self.device}:v4"

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
        with self._lock:
            for item in batch:
                sample_rate = int(item.audio.sample_rate)
                if sample_rate <= 0:
                    raise ValueError(
                        "PhoneticXeus requires a positive audio sample rate"
                    )
                waveform = np.frombuffer(item.audio.pcm_f32le, dtype="<f4")
                results = []
                for number, utterance in enumerate(item.utterances):
                    start = utterance.start_ms * sample_rate // 1000
                    end = utterance.end_ms * sample_rate // 1000
                    if not 0 <= start < end <= len(waveform):
                        raise ValueError(
                            f"Utterance {utterance.index} is outside the audio"
                        )
                    spoken = [unit for unit in utterance.units if not unit.pause]
                    references = [
                        self.pronunciations(unit.text, item.language) for unit in spoken
                    ]
                    ipa = []
                    if spoken:
                        if self._model is None:
                            # Loading a local pinned snapshot also pins the wrapper's
                            # internal pxeus import, which otherwise fetches main.
                            path = snapshot_download(
                                self.model_id,
                                revision=self.revision,
                                allow_patterns=[
                                    "*.json",
                                    "*.py",
                                    "model.safetensors",
                                    "pxeus/**",
                                ],
                            )
                            device = self.device or (
                                "cuda" if torch.cuda.is_available() else "cpu"
                            )
                            self._model = (
                                AutoModel.from_pretrained(path, trust_remote_code=True)
                                .to(device)
                                .eval()
                            )
                        audio = torch.from_numpy(waveform[start:end].copy())
                        if sample_rate != 16000:
                            audio = audio_ops.resample(audio, sample_rate, 16000)
                        raw = self._model.transcribe(audio, sampling_rate=16000)[0][
                            "predicted_transcript"
                        ]
                        phones = [
                            phone
                            for phone in raw.split("/")
                            if phone
                            and not (phone.startswith("<") and phone.endswith(">"))
                        ]
                        ipa = project_phones(phones, references)
                    observed = iter(ipa)
                    results.append(
                        PhoneticResult(
                            index=utterance.index,
                            ipa=[
                                unit.text if unit.pause else next(observed)
                                for unit in utterance.units
                            ],
                        )
                    )
                    if progress:
                        progress(number + 1, len(item.utterances))
                outputs.append(
                    PhoneticOutput(source_id=item.source_id, utterances=results)
                )
        return outputs
