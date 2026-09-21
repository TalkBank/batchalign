"""Whisper precision must fit the platform's supported CPU kernels."""
from types import ModuleType, SimpleNamespace
import sys

import pytest


@pytest.mark.parametrize('device,cuda,mps,cpu', [
    ('cpu', True, False, True),
    ('cpu:0', False, True, True),
    (None, False, False, True),
    (None, True, False, False),
    (None, False, True, True),
    ('cuda:0', True, False, False),
    ('mps', False, True, False),
])
def test_whisper_cpu_selects_supported_dtype_before_inference(monkeypatch, device, cuda, mps, cpu):
    import torch
    from batchalign.backends.asr.whisper import WhisperBackend, _cpu_dtype
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
            assert kwargs['device'].startswith('cpu')
            assert kwargs.get('dtype') == _cpu_dtype(torch)
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


@pytest.mark.parametrize('system,machine,version,expected', [
    ('darwin', 'arm64', '2.8.0', 'half'),
    ('darwin', 'arm64', '2.5.0', 'half'),
    ('darwin', 'arm64', '2.10.0+cpu', 'half'),
    ('darwin', 'arm64', '2.3.1', 'single'),
    ('darwin', 'x86_64', '2.2.2', 'single'),
    ('darwin', 'x86_64', '2.8.0', 'single'),
    ('linux', 'aarch64', '2.8.0', 'single'),
    ('linux', 'x86_64', '2.8.0', 'single'),
    ('win32', 'AMD64', '2.8.0', 'single'),
])
def test_cpu_precision_compatibility_policy(monkeypatch, system, machine, version, expected):
    from batchalign.backends.asr import whisper

    monkeypatch.setattr(whisper.sys, 'platform', system)
    monkeypatch.setattr(whisper.platform, 'machine', lambda: machine)
    torch = SimpleNamespace(__version__=version, float16='half', float32='single')
    assert whisper._cpu_dtype(torch) == expected
