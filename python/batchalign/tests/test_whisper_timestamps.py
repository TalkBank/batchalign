"""Model timestamp regressions through the real ASR/CHAT pipeline."""
import wave
from itertools import combinations_with_replacement, product
from random import Random

from batchalign.backends.asr.whisper import WhisperBackend, _monotonic_boundaries
from batchalign.backends.base import BatchPolicy


def test_whisper_timestamp_projection_minimizes_error_without_reordering():
    # Exhaustive independent oracle for small sequences, including nested
    # reversals that a one-pair overlap adjustment cannot repair.
    candidates = list(combinations_with_replacement(range(4), 4))
    for values in product(range(4), repeat=4):
        actual = _monotonic_boundaries(list(values))
        error = sum((left - right) ** 2 for left, right in zip(values, actual))
        best = min(sum((left - right) ** 2 for left, right in zip(values, candidate))
                   for candidate in candidates)
        assert error == best


def test_whisper_timestamp_projection_properties():
    rng = Random(20260921)
    for _ in range(1000):
        values = [rng.randrange(20001) for _ in range(rng.randrange(1, 101))]
        actual = _monotonic_boundaries(values)
        assert len(actual) == len(values)
        assert actual == sorted(actual)
        assert min(values) <= actual[0] <= actual[-1] <= max(values)
        assert _monotonic_boundaries(actual) == actual
        ordered = sorted(values)
        assert _monotonic_boundaries(ordered) == ordered
    assert _monotonic_boundaries([]) == []


def test_whisper_overlapping_chunk_timestamps_serialize_valid_chat(tmp_path):
    from batchalign._core import CacheSpec
    from batchalign.inputs import media_from_path
    from batchalign.recipes import transcribe

    audio = tmp_path / 'overlap.wav'
    with wave.open(str(audio), 'wb') as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(16000)
        stream.writeframes(b'\0\0' * 320000)
    backend = WhisperBackend.__new__(WhisperBackend)
    backend._model = 'fixture'
    backend._language = 'English'
    backend._policy = BatchPolicy(max_size=1, window_ms=0)
    backend._pipe = lambda *args, **kwargs: {
        'text': 'Hello world. Another sentence.',
        'chunks': [
            {'text': 'Hello', 'timestamp': (8, 9)},
            {'text': ' world.', 'timestamp': (9, 11)},
            {'text': ' Another', 'timestamp': (10, 11)},
            {'text': ' sentence.', 'timestamp': (11, 12)},
        ],
    }
    pipeline = transcribe(asr_backend=backend, workers=1, cache=CacheSpec.bypass())
    outcome, = pipeline.run([media_from_path(audio)])
    assert not outcome.is_failed, outcome.error
    output = tmp_path / 'result.cha'
    outcome.write(str(output))
    chat = output.read_text()
    assert 'Hello world .' in chat
    assert 'Another sentence .' in chat
    assert chat.count('%wor:') == 2
