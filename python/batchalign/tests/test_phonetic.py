"""Phone ownership, packaged pronunciation data, and the real CLI/runner seam."""

from __future__ import annotations

import wave
import base64
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from batchalign.backends.phonetic.pronunciation import Pronunciations
from batchalign.backends.phonetic.projection import comparison_symbols, project_phones
from batchalign.cli import app


@pytest.mark.parametrize(
    "phones,reference,expected",
    [
        (["ð", "ə", "k", "æ", "t"], ["ðə", "kæt"], ["ðə", "kæt"]),
        # A substitution must retain the observed t, not canonical k.
        (["ð", "ə", "t", "æ", "t"], ["ðə", "kæt"], ["ðə", "tæt"]),
        (["ð", "ə", "kʰ", "æ̃", "t", "s"], ["ðə", "kæt"], ["ðə", "kʰæ̃ts"]),
        (["ə", "b", "b", "ə"], ["əb", "bə"], ["əb", "bə"]),
        (["aɪ", "s", "iː"], ["aɪ", "si"], ["aɪ", "siː"]),
        (["s", "ə", "k", "æ", "t"], ["ðə", "kæt"], ["sə", "kæt"]),
    ],
)
def test_projection_preserves_observed_phones(phones, reference, expected):
    assert project_phones(phones, reference) == expected
    assert "".join(expected) == "".join(phones)


def test_projection_rejects_unresolved_units():
    with pytest.raises(ValueError, match="unresolved"):
        project_phones(["k", "æ", "t"], ["ðə", "kæt"])
    with pytest.raises(ValueError, match="empty"):
        project_phones([], ["kæt"])


def test_comparison_normalization_does_not_split_combining_marks():
    assert comparison_symbols("ˈkʰæ̃tː") == list("kæt")
    assert comparison_symbols("ɚ") == list("əɹ")


def test_packaged_lookup_and_overrides():
    lookup = Pronunciations({"wug": "wʌɡ", "bonjour": "bɔ̃ʒuʁ"})
    assert lookup("cat", "eng") == "kæt"
    assert lookup("&-um", "eng")
    assert lookup("wug", "eng") == "wʌɡ"
    assert lookup("bonjour", "fra") == "bɔ̃ʒuʁ"
    with pytest.raises(ValueError, match="override"):
        lookup("zzzzunlistedword", "eng")
    with pytest.raises(ValueError, match="override"):
        lookup("chat", "fra")


@pytest.fixture
def transcript(tmp_path):
    path = tmp_path / "sample.cha"
    path.write_text(
        "@UTF8\n@Begin\n@Languages:\teng\n@Participants:\tPAR Participant\n"
        "@ID:\teng|test|PAR|||||Participant|||\n@Media:\trecording, audio\n"
        "*PAR:\tthe (.) cat . \x150_1000\x15\n@End\n",
        encoding="utf-8",
    )
    with wave.open(str(tmp_path / "recording.wav"), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16000)
        audio.writeframes(b"\x00\x00" * 16000)
    return path


@pytest.fixture
def fake_backend(monkeypatch):
    import batchalign as ba
    from batchalign._core.proto import PhoneticOutput, PhoneticResult

    class FakePhonetic(ba.Phonetic):
        calls = []
        corrupt = False

        @property
        def name(self):
            # Distinct cache namespace per test instance.
            return f"phonetic-test-{id(self)}"

        @property
        def batch_policy(self):
            return ba.BatchPolicy.one()

        def call(self, batch, **kwargs):
            self.calls.extend(batch)
            outputs = []
            for item in batch:
                utterances = []
                for utterance in item.utterances:
                    ipa = [
                        unit.text if unit.pause else "tə" for unit in utterance.units
                    ]
                    if self.corrupt:
                        ipa.pop()
                    utterances.append(PhoneticResult(index=utterance.index, ipa=ipa))
                outputs.append(
                    PhoneticOutput(source_id=item.source_id, utterances=utterances)
                )
            return outputs

    backend = FakePhonetic()
    monkeypatch.setattr(ba, "PhoneticXeusBackend", lambda **kwargs: backend)
    return backend


def test_cli_runner_writes_pho_and_preserves_existing(
    transcript, fake_backend, tmp_path
):
    output = tmp_path / "out"
    result = CliRunner().invoke(
        app, ["phonetic", str(transcript), "--out", str(output)]
    )
    assert result.exit_code == 0, result.output
    text = (output / transcript.name).read_text()
    assert "%pho:\ttə (.) tə" in text
    assert "%pho:" not in transcript.read_text()
    units = fake_backend.calls[0].utterances[0].units
    assert [(unit.text, unit.pause) for unit in units] == [
        ("the", False),
        ("(.)", True),
        ("cat", False),
    ]
    # Existing tiers skip inference, even without media in the output folder.
    calls = len(fake_backend.calls)
    result = CliRunner().invoke(app, ["phonetic", str(output / transcript.name)])
    assert result.exit_code == 0, result.output
    assert len(fake_backend.calls) == calls


def test_cli_failure_does_not_overwrite_source(transcript, fake_backend):
    fake_backend.corrupt = True
    original = transcript.read_bytes()
    result = CliRunner().invoke(app, ["phonetic", str(transcript)])
    assert result.exit_code != 0
    assert transcript.read_bytes() == original


def test_cli_requires_utterance_timing(transcript, fake_backend):
    transcript.write_text(
        transcript.read_text()
        .replace(" \x150_1000\x15", "")
        .replace("recording, audio", "recording, audio, unlinked")
    )
    result = CliRunner().invoke(app, ["phonetic", str(transcript)])
    assert result.exit_code != 0
    assert "run utr first" in result.output
    assert not fake_backend.calls


def test_cli_help_is_lazy():
    result = CliRunner().invoke(app, ["phonetic", "--help"])
    assert result.exit_code == 0
    assert "--pronunciations" in result.output


def test_backend_resamples_and_retains_phone_tokens():
    from batchalign.backends.phonetic.xeus import PhoneticXeusBackend
    from batchalign._core.proto import PreparedAudio

    calls = []

    class Model:
        def transcribe(self, audio, sampling_rate):
            calls.append((len(audio), sampling_rate))
            return [{"predicted_transcript": "<blank>/kʰ/æ̃/t"}]

    backend = PhoneticXeusBackend()
    backend._model = Model()
    item = SimpleNamespace(
        source_id="sample",
        language="eng",
        audio=PreparedAudio(
            pcm_f32le=base64.b64encode(b"\x00" * 22050 * 4),
            sample_rate=22050,
            channels=1,
            frame_count=22050,
        ),
        utterances=[
            SimpleNamespace(
                index=0,
                start_ms=0,
                end_ms=1000,
                units=[SimpleNamespace(text="cat", pause=False)],
            )
        ],
    )
    output = backend.call([item])
    assert calls == [(16000, 16000)]
    assert output[0].utterances[0].ipa == ["kʰæ̃t"]
    item.utterances[0].end_ms = 2000
    with pytest.raises(ValueError, match="outside"):
        backend.call([item])


def test_backend_identity_tracks_pronunciations_and_pins_revision():
    from batchalign.backends.phonetic.xeus import PhoneticXeusBackend

    default = PhoneticXeusBackend()
    override = PhoneticXeusBackend(pronunciations={"cat": "kɛt"})
    assert default.name != override.name
    assert override.name == PhoneticXeusBackend(pronunciations={"cat": "kɛt"}).name
    with pytest.raises(ValueError, match="immutable"):
        PhoneticXeusBackend(revision="main")
