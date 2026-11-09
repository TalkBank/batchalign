"""DrivenData's English child-speech WavLM CTC phone recognizer."""

from __future__ import annotations

from typing import Any, Mapping

from .xeus import PhoneticXeusBackend
from .utils.projection import comparison_symbols

MODEL = "drivendata/pasketti-phonetic"
REVISION = "675dfe392a2af7050f1374eeab4458cb1f003b3e"


class PaskettiPhoneticBackend(PhoneticXeusBackend):
    """Reuse CHAT ownership/projection with a standard, full-precision CTC model."""

    def __init__(
        self, *, model: str = MODEL, revision: str = REVISION,
        device: str | None = None,
        pronunciations: Mapping[str, str] | None = None,
        batch_size: int | None = None,
    ):
        super().__init__(
            model=model, revision=revision, device=device,
            pronunciations=pronunciations, batch_size=batch_size,
        )
        self._processor = None

    @property
    def name(self) -> str:
        return super().name.replace("phoneticxeus:", "pasketti-phonetic:", 1) + ":v1"

    def _group_utterances(self, utterances: list[Any]) -> list[list[int]]:
        # This checkpoint expects single-speaker utterances; never combine turns.
        return [[index] for index in range(len(utterances))]

    def _load_model(self, device: str) -> None:
        import torch
        from transformers import Wav2Vec2Processor, WavLMForCTC

        self._processor = Wav2Vec2Processor.from_pretrained(
            self.model_id, revision=self.revision,
        )
        # Half precision can produce NaNs in WavLM's relative position bias.
        self._model = WavLMForCTC.from_pretrained(
            self.model_id, revision=self.revision, torch_dtype=torch.float32,
        ).to(device).eval()

    def _transcribe_batch(self, audio_batch: list[Any]) -> list[list[str]]:
        import torch

        inputs = self._processor(
            [audio.cpu().numpy() for audio in audio_batch],
            sampling_rate=16000, padding=True, return_attention_mask=True,
            return_tensors="pt",
        ).to(self._model.device)
        with torch.inference_mode():
            ids = self._model(**inputs).logits.argmax(-1)
            lengths = self._model._get_feat_extract_output_lengths(
                inputs["attention_mask"].sum(-1)
            )
            padding = torch.arange(ids.shape[1], device=ids.device) >= lengths[:, None]
            ids[padding] = self._processor.tokenizer.pad_token_id
            texts = self._processor.batch_decode(ids)
        return [comparison_symbols(text) for text in texts]

    def call(self, batch: list[Any], *, progress: Any = None, **kwargs: Any) -> list[Any]:
        for item in batch:
            if item.language != "eng":
                raise ValueError("Pasketti phonetic supports English (eng) only")
        return super().call(batch, progress=progress, **kwargs)
