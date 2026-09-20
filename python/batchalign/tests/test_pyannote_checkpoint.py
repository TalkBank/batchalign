"""Public diarization checkpoints retain restricted Torch loading semantics."""
from types import ModuleType
import sys

import pytest


@pytest.mark.parametrize("fail", [False, True])
def test_checkpoint_allowlist_is_scoped_to_pipeline_load(tmp_path, monkeypatch, fail):
    import torch
    from batchalign.backends.speaker.pyannote import PyannoteBackend

    if not hasattr(torch.serialization, "safe_globals"):
        pytest.skip("Torch 2.2 has no scoped safe-globals API")
    checkpoint = tmp_path / 'metadata.pt'
    torch.save({'version': torch.torch_version.TorchVersion('2.0.0')}, checkpoint)
    before = torch.serialization.get_safe_globals().copy()
    assert torch.torch_version.TorchVersion not in before

    class Pipeline:
        @staticmethod
        def from_pretrained(model, *, token):
            assert model == 'talkbank/dia-fork'
            assert torch.load(checkpoint, weights_only=True)['version'] == '2.0.0'
            if fail:
                raise RuntimeError('provider unavailable')
            return object()

    audio = ModuleType('pyannote.audio')
    audio.Pipeline = Pipeline
    task = ModuleType('pyannote.audio.core.task')
    for name in ('Specifications', 'Problem', 'Resolution'):
        setattr(task, name, type(name, (), {}))
    monkeypatch.setitem(sys.modules, 'pyannote.audio', audio)
    monkeypatch.setitem(sys.modules, 'pyannote.audio.core.task', task)
    if fail:
        with pytest.raises(RuntimeError, match='provider unavailable'):
            PyannoteBackend(hf_token='')
    else:
        assert PyannoteBackend(hf_token='').name.startswith('pyannote:talkbank/dia-fork:')
    assert torch.serialization.get_safe_globals() == before
