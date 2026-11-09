"""Pasketti engine selection and CTC decoding contracts (no weight downloads)."""

from types import SimpleNamespace

import pytest
import typer

from batchalign.backends.phonetic.pasketti import PaskettiPhoneticBackend
from batchalign.cli.transcribe import AsrEngine, _build_asr
from batchalign.lang import LanguageCode


def test_word_engine_selects_checkpoint_and_device():
    calls = []
    sentinel = object()
    ba = SimpleNamespace(Qwen3AsrBackend=lambda **kw: calls.append(kw) or sentinel)
    backend, diarizes = _build_asr(
        ba, AsrEngine.pasketti, None, LanguageCode.from_str("eng"), device="cpu",
    )
    assert backend is sentinel
    assert not diarizes
    assert calls[0]["model_id"] == "drivendata/pasketti-word"
    assert calls[0]["device"] == "cpu"
    _build_asr(ba, AsrEngine.pasketti, "custom/model", LanguageCode.from_str("eng"))
    assert calls[1]["model_id"] == "custom/model"
    with pytest.raises(typer.BadParameter, match="English"):
        _build_asr(ba, AsrEngine.pasketti, None, LanguageCode.from_str("fra"))


def test_phonetic_public_surface_and_cache_identity():
    import batchalign as ba
    from batchalign.backends.phonetic.xeus import PhoneticXeusBackend

    assert ba.PaskettiPhoneticBackend is PaskettiPhoneticBackend
    backend = PaskettiPhoneticBackend()
    assert backend.name.startswith("pasketti-phonetic:drivendata/pasketti-phonetic:")
    assert backend.name != PhoneticXeusBackend().name
    assert backend.name != PaskettiPhoneticBackend(pronunciations={"cat": "kæt"}).name
    with pytest.raises(ValueError, match="English"):
        backend.call([SimpleNamespace(language="fra")])


def test_ctc_masks_padding_and_preserves_ipa():
    import torch

    class Inputs(dict):
        def to(self, device):
            return self

    class Processor:
        tokenizer = SimpleNamespace(pad_token_id=0)

        def __call__(self, waves, **kwargs):
            assert [len(w) for w in waves] == [4, 8]
            assert kwargs["sampling_rate"] == 16000
            assert kwargs["return_attention_mask"]
            return Inputs(attention_mask=torch.tensor([[1]*4 + [0]*4, [1]*8]))

        def batch_decode(self, ids):
            assert ids.tolist() == [[1, 1, 0, 0], [1, 1, 1, 1]]
            return ["k æ̃ t", "d a͡ɪ"]

    class Model:
        device = "cpu"

        def __call__(self, **kwargs):
            return SimpleNamespace(logits=torch.tensor([[[0., 1.]]*4]*2))

        def _get_feat_extract_output_lengths(self, lengths):
            return lengths // 2

    backend = PaskettiPhoneticBackend()
    backend._model = Model()
    backend._processor = Processor()
    assert backend._transcribe_batch([torch.zeros(4), torch.zeros(8)]) == [
        ["k", "æ̃", "t"], ["d", "a͡ɪ"],
    ]


def test_phonetic_cli_selects_pasketti(tmp_path, monkeypatch):
    from typer.testing import CliRunner
    import batchalign as ba
    from batchalign.cli import app

    calls = []

    def selected(**kwargs):
        calls.append(kwargs)
        raise RuntimeError("pasketti selected")

    monkeypatch.setattr(ba, "PaskettiPhoneticBackend", selected)
    result = CliRunner().invoke(
        app, ["phonetic", str(tmp_path), "--engine", "pasketti", "--force-cpu", "--batch-size", "3"],
    )
    assert calls == [{"device": "cpu", "pronunciations": None, "batch_size": 3}]
    assert result.exit_code == 2
    assert "pasketti selected" in result.output


def test_phonetic_loader_pins_revision_and_full_precision(monkeypatch):
    import torch
    import transformers

    calls = []

    class Model:
        def to(self, device):
            assert device == "cpu"
            return self

        def eval(self):
            return self

    def processor(model_id, **kwargs):
        calls.append(("processor", model_id, kwargs))
        return object()

    def model(model_id, **kwargs):
        calls.append(("model", model_id, kwargs))
        return Model()

    monkeypatch.setattr(transformers.Wav2Vec2Processor, "from_pretrained", processor)
    monkeypatch.setattr(transformers.WavLMForCTC, "from_pretrained", model)
    backend = PaskettiPhoneticBackend()
    backend._load_model("cpu")
    assert calls == [
        ("processor", backend.model_id, {"revision": backend.revision}),
        ("model", backend.model_id, {"revision": backend.revision, "torch_dtype": torch.float32}),
    ]
    assert backend._group_utterances([object(), object()]) == [[0], [1]]
