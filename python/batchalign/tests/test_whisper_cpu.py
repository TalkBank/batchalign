"""Whisper CPU loading must not inherit unsupported half precision."""
from types import ModuleType, SimpleNamespace
import sys

import pytest


@pytest.mark.parametrize('device,cuda,mps,cpu', [
    ('cpu', True, False, True),
    ('cpu:0', False, True, True),
    (None, False, False, True),
    (None, True, False, False),
    (None, False, True, False),
    ('cuda:0', True, False, False),
    ('mps', False, True, False),
])
def test_whisper_cpu_loads_float32_before_inference(monkeypatch, device, cuda, mps, cpu):
    import torch
    from batchalign.backends.asr.whisper import WhisperBackend
    from batchalign.lang import LanguageCode

    monkeypatch.setattr(torch.cuda, 'is_available', lambda: cuda)
    monkeypatch.setattr(torch.backends.mps, 'is_available', lambda: mps)
    monkeypatch.setattr('batchalign.backends.asr._torch_audio.disable_torchcodec', lambda: None)
    called = []

    def pipeline(task, **kwargs):
        called.append(kwargs)
        # A tiny real CPU kernel checks the selected loading dtype without
        # downloading Whisper or allocating its weights.
        if cpu:
            assert kwargs.get('dtype') == torch.float32
            torch.nn.functional.layer_norm(torch.ones(1, 4, dtype=kwargs['dtype']), (4,))
        else:
            assert 'dtype' not in kwargs
        return SimpleNamespace()

    transformers = ModuleType('transformers')
    transformers.pipeline = pipeline
    monkeypatch.setitem(sys.modules, 'transformers', transformers)
    english = WhisperBackend(language=LanguageCode.from_str('eng'), device=device)
    spanish = WhisperBackend(language=LanguageCode.from_str('spa'), device=device)
    assert english.name != spanish.name
    assert len(called) == 2
