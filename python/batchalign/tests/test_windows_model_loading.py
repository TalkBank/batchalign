"""Exercise real safetensors/Transformers loading without model downloads."""
import sys

import pytest

from batchalign.backends import _transformers


@pytest.mark.parametrize("platform", ["darwin", "linux"])
def test_other_platforms_keep_transformers_loader(monkeypatch, platform):
    from transformers import modeling_utils

    original = modeling_utils.safe_open
    monkeypatch.setattr(_transformers.sys, "platform", platform)
    _transformers.configure_windows_loading()
    assert modeling_utils.safe_open is original


@pytest.mark.skipif(sys.platform != "win32", reason="Windows safetensors loading")
def test_streaming_load_preserves_model_weights_and_output(tmp_path, monkeypatch):
    import safetensors
    import torch
    from transformers import M2M100Config, M2M100ForConditionalGeneration, modeling_utils

    torch.manual_seed(7)
    config = M2M100Config(vocab_size=32, d_model=16, encoder_layers=1, decoder_layers=1,
                         encoder_attention_heads=2, decoder_attention_heads=2,
                         encoder_ffn_dim=32, decoder_ffn_dim=32)
    original = M2M100ForConditionalGeneration(config).eval()
    original.save_pretrained(tmp_path, safe_serialization=True)
    calls = []
    safe_open = safetensors.safe_open

    def record(*args, **kwargs):
        calls.append(kwargs.get("backend"))
        return safe_open(*args, **kwargs)

    monkeypatch.setattr(safetensors, "safe_open", record)
    # Register the original so pytest restores the process-global adapter.
    monkeypatch.setattr(modeling_utils, "safe_open", modeling_utils.safe_open)
    _transformers.configure_windows_loading()
    _transformers.configure_windows_loading()
    loaded = M2M100ForConditionalGeneration.from_pretrained(tmp_path, local_files_only=True).eval()
    assert calls and set(calls) == {"pread"}
    for name, tensor in original.state_dict().items():
        torch.testing.assert_close(loaded.state_dict()[name], tensor, rtol=0, atol=0)
    inputs = {"input_ids": torch.tensor([[4, 5, 2]]),
              "decoder_input_ids": torch.tensor([[2, 7]])}
    with torch.inference_mode():
        torch.testing.assert_close(loaded(**inputs).logits, original(**inputs).logits)
