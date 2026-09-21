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


@pytest.mark.parametrize("timed", [True, False])
@pytest.mark.parametrize("media_stem", ["clip", "recording", "recording.part"])
def test_native_recovery_dispatch_depends_on_existing_timing(tmp_path, timed, media_stem):
    import wave
    from batchalign._core import Pipeline, Task, CacheSpec
    from batchalign.inputs import chat_from_path

    source = tmp_path / 'clip.cha'
    source.write_text('@UTF8\n@Begin\n@Languages:\teng\n'
                      '@Participants:\tPAR Participant\n'
                      '@ID:\teng|test|PAR|||||Participant|||\n'
                      f'@Media:\t{media_stem}, audio' + ('' if timed else ', unlinked') + '\n'
                      + '*PAR:\thello world . ' + ('\x15200_900\x15' if timed else '') + '\n@End\n', encoding='utf8')
    with wave.open(str(tmp_path / f'{media_stem}.wav'), 'wb') as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16000)
        audio.writeframes(b'\0\0' * 16000)
    with patch('batchalign.backends.asr.whisper.WhisperBackend') as factory:
        from batchalign._core.proto import AsrOutput, AsrSegment, AsrWord
        factory.return_value.call.return_value = [AsrOutput(source_id=str(source), segments=[
            AsrSegment(start_ms=100, end_ms=700, text='hello world', speaker=None, words=[
                AsrWord(text='hello', start_ms=100, end_ms=300, confidence=None),
                AsrWord(text='world', start_ms=400, end_ms=700, confidence=None),
            ])
        ])]
        recovery = DesktopTimingRecovery(device='cpu')
        pipeline = Pipeline(tasks=[Task.Utr], backends=[recovery], workers=1, cache=CacheSpec.bypass())
        outcomes = pipeline.run([chat_from_path(source, source_id=str(source))])
        assert len(outcomes) == 1
        assert not outcomes[0].is_failed, outcomes[0].error
        output = tmp_path / 'result.cha'
        outcomes[0].write(str(output))
        written = output.read_text(encoding='utf8')
        if timed:
            assert '\x15200_900\x15' in written
            factory.assert_not_called()
        else:
            assert '\x15100_700\x15' in written
            assert ', unlinked' not in written
            factory.assert_called_once()
            factory.return_value.call.assert_called_once()
