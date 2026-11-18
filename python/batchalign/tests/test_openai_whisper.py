"""The desktop's OpenAI Whisper choice must not require a system decoder."""
import base64
from types import SimpleNamespace

import numpy as np

from batchalign._core.proto import AsrInput, AsrOptions, PreparedAudio
from batchalign.backends.asr.openai_whisper import OpenAIWhisperBackend


def test_openai_whisper_uses_decoded_audio_and_preserves_word_timing():
    samples = np.array([0.1, -0.2, 0.3, 0], dtype="<f4")
    def transcribe(audio, **kwargs):
        # A file path would invoke ffmpeg and break on a clean installation.
        np.testing.assert_array_equal(audio, samples)
        assert audio.flags.writeable
        assert kwargs == {"word_timestamps": True, "language": "en"}
        return {"segments": [{"start": 0, "end": 1, "text": "Hello world.", "words": [
            {"word": " Hello", "start": 0, "end": .4, "probability": .9},
            {"word": " world.", "start": .4, "end": 1, "probability": .8},
        ]}]}
    backend = OpenAIWhisperBackend.__new__(OpenAIWhisperBackend)
    backend._model = SimpleNamespace(transcribe=transcribe)
    backend._language = "en"
    item = AsrInput(source_id="clip", language={"kind": "code", "value": "eng"},
                    options=AsrOptions(), audio=PreparedAudio(
                        pcm_f32le=base64.b64encode(samples.tobytes()).decode(),
                        sample_rate=16000, channels=1, frame_count=4))
    output, = backend.call([item])
    assert output.source_id == "clip"
    segment, = output.segments
    assert segment.text == "Hello world"
    assert [(word.text, word.start_ms, word.end_ms) for word in segment.words] == [
        ("Hello", 0, 400), ("world.", 400, 1000)]
