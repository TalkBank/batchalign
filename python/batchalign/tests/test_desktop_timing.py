"""Desktop timing policy tests; model inference is covered separately in CI."""
from unittest.mock import Mock, patch

import pytest

from batchalign.desktop_timing import DesktopTimingRecovery


def test_timing_recovery_does_not_load_whisper_until_native_runner_dispatches():
    with patch('batchalign.backends.asr.whisper.WhisperBackend') as factory:
        backend = DesktopTimingRecovery(device='cpu')
        assert backend.name
        assert backend.batch_policy.max_size == 1
        assert backend.call([]) == []
        factory.assert_not_called()
        items = [Mock()]
        factory.return_value.call.return_value = ['recovered']
        assert backend.call(items) == ['recovered']
        assert backend.call(items) == ['recovered']
        factory.assert_called_once()
        assert factory.call_args.kwargs['device'] == 'cpu'
        assert factory.return_value.call.call_count == 2


def test_failed_model_load_remains_retryable_and_is_not_a_success():
    with patch('batchalign.backends.asr.whisper.WhisperBackend') as factory:
        factory.side_effect = RuntimeError('model download failed')
        backend = DesktopTimingRecovery()
        with pytest.raises(RuntimeError, match='model download failed'):
            backend.call([Mock()])
        factory.side_effect = None
        factory.return_value.call.return_value = ['recovered']
        assert backend.call([Mock()]) == ['recovered']
        assert factory.call_count == 2
