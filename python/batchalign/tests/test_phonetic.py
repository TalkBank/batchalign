"""Phone ownership, multilingual IPA references, and the real CLI/runner seam."""

from __future__ import annotations

import wave
import base64
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from batchalign.backends.phonetic.utils.pronunciation import (
    Pronunciations, epitran_code, load_pronunciations,
)
from batchalign.backends.phonetic.utils.projection import comparison_symbols, project_phones
from batchalign.backends.phonetic.utils.piper import piper_ipa
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
    assert comparison_symbols("ˈkʰæ̃tː") == ["kʰ", "æ̃", "tː"]
    assert comparison_symbols("ã") == comparison_symbols("a\u0303")
    assert comparison_symbols("t͡ʃ") == ["t͡ʃ"]
    assert comparison_symbols("rɹɚɝʌəɐ") == list("rɹɚɝʌəɐ")
    assert comparison_symbols("a˥a˩") == list("a˥a˩")


@pytest.mark.parametrize(
    "language,word,ipa",
    [("spa", "gato", "ɡato"), ("tur", "göz", "ɡœz"), ("fra", "chat", "ʃa")],
)
def test_multilingual_ipa_references(language, word, ipa):
    reference = Pronunciations()(word, language)
    assert comparison_symbols(reference) == comparison_symbols(ipa)
    # The same DP groups directly against generated IPA for each language.
    phones = comparison_symbols(ipa) * 2
    assert project_phones(phones, [reference, reference]) == [ipa, ipa]


def test_automatic_non_latin_script():
    assert Pronunciations()("кот", "rus") == "kot"


@pytest.mark.parametrize(
    "language,code",
    [("fra", "fra-Latn"), ("rus", "rus-Cyrl"), ("hin", "hin-Deva"),
     ("ara", "ara-Arab"), ("cmn", "cmn-Hans"), ("zho", "cmn-Hans"),
     ("yue", "yue-Hant"), ("jpn", "jpn-Jpan")],
)
def test_language_selects_epitran_script(language, code):
    assert epitran_code(language) == code


def test_lookup_overrides_and_chat_markers():
    lookup = Pronunciations({"wug": "wʌɡ", "bonjour": "bɔ̃ʒuʁ"})
    assert comparison_symbols(lookup("&-gato", "spa")) == list("ɡato")
    assert comparison_symbols(lookup("‹gato gato›", "spa")) == list("ɡatoɡato")
    assert lookup("wug", "eng") == "wʌɡ"
    assert lookup("bonjour", "fra") == "bɔ̃ʒuʁ"
    with pytest.raises(ValueError, match="@Languages"):
        lookup("word", "ell")  # A valid CHAT language without an Epitran map.
    with pytest.raises(ValueError, match="Incomplete IPA"):
        lookup("göz猫", "tur")


def test_pronunciation_csv(tmp_path):
    path = tmp_path / "pronunciations.csv"
    path.write_text('\ufeffword,ipa\nWug,wʌɡ\n"the cat",ðəkæt\n"a,b",ab\n\n')
    overrides = load_pronunciations(path)
    assert overrides == {"wug": "wʌɡ", "the cat": "ðəkæt", "a,b": "ab"}
    assert Pronunciations(overrides)("WUG", "eng") == "wʌɡ"


@pytest.mark.parametrize(
    "contents,error",
    [
        ('{"wug": "wʌɡ"}', "header word,ipa"),
        ("word,ipa\nwug,\n", "nonempty"),
        ("word,ipa\nwug,wʌɡ,extra\n", "nonempty"),
        ("word,ipa\nwug,wʌɡ\nWUG,wʊɡ\n", "duplicate"),
        ('word,ipa\n"wug,wʌɡ\n', "Invalid pronunciation CSV"),
    ],
)
def test_pronunciation_csv_rejects_invalid_input(tmp_path, contents, error):
    path = tmp_path / "pronunciations.csv"
    path.write_text(contents)
    with pytest.raises(ValueError, match=error):
        load_pronunciations(path)


def test_english_uses_piper_without_flite(monkeypatch, tmp_path):
    import nltk

    monkeypatch.setattr(nltk.data, "path", [str(tmp_path)])
    monkeypatch.setattr("shutil.which", lambda _: None)
    def no_epitran(*args):
        pytest.fail("English must not use Epitran")
    monkeypatch.setattr(Pronunciations, "_epitran_engine", no_epitran)
    assert comparison_symbols(Pronunciations()("cat", "eng")) == list("kæt")
    assert Pronunciations({"cat": "kæt"})("cat", "eng") == "kæt"


def test_piper_failure_does_not_silently_fall_back(monkeypatch):
    import piper_plus_g2p

    def broken(code):
        raise RuntimeError("Piper unavailable")

    monkeypatch.setattr(piper_plus_g2p, "get_phonemizer", broken)
    with pytest.raises(RuntimeError, match="Piper unavailable"):
        Pronunciations()("gato", "spa")
    # Explicit overrides still bypass G2P entirely.
    assert Pronunciations({"cat": "kæt"})("cat", "eng") == "kæt"


def test_unsupported_piper_language_uses_epitran(monkeypatch):
    import piper_plus_g2p

    def no_piper(code):
        pytest.fail("Russian must use Epitran")

    monkeypatch.setattr(piper_plus_g2p, "get_phonemizer", no_piper)
    assert Pronunciations()("кот", "rus") == "kot"


@pytest.mark.parametrize("language", ["cmn", "zho"])
def test_mandarin_piper_tones(language):
    assert Pronunciations()("你", language) == "ni˨˩˦"


@pytest.mark.parametrize("language,word,expected", [("jpn", "猫", "neko"), ("kor", "가", "ka")])
def test_piper_asian_backends(language, word, expected, monkeypatch, tmp_path):
    import nltk

    monkeypatch.setattr(nltk.data, "path", [str(tmp_path)])
    assert Pronunciations()(word, language) == expected


@pytest.mark.parametrize(
    "language,tokens,expected",
    [
        ("zh", ["n", "i", "tone3", "x", "au", "tone4"], "ni˨˩˦xau˥˩"),
        ("ja", ["k", "o", "[", "N_n", "n", "i", "ch", "i", "w", "a"], "konnitɕiwa"),
        ("ja", ["k", "i", "cl", "t", "e", "]"], "kitte"),
        ("es", ["p", "e", "rr", "o"], "pero"),
    ],
)
def test_piper_labels_are_converted_to_ipa(language, tokens, expected):
    assert piper_ipa(tokens, language) == expected


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


@pytest.mark.parametrize("language", ["eng", "fra", "rus"])
def test_cli_runner_writes_pho_and_preserves_existing(
    transcript, fake_backend, tmp_path, language
):
    transcript.write_text(transcript.read_text().replace("eng", language))
    output = tmp_path / "out"
    result = CliRunner().invoke(
        app, ["phonetic", str(transcript), "--out", str(output)]
    )
    assert result.exit_code == 0, result.output
    text = (output / transcript.name).read_text()
    assert "%pho:\ttə (.) tə" in text
    assert "%pho:" not in transcript.read_text()
    units = fake_backend.calls[0].utterances[0].units
    assert fake_backend.calls[0].language == language
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
    assert "word,ipa" in result.output
    assert "wug,wʌɡ" in result.output
    assert "--g2p-code" not in result.output


def test_cli_loads_csv_overrides(transcript, fake_backend, tmp_path, monkeypatch):
    import batchalign as ba

    path = tmp_path / "pronunciations.csv"
    path.write_text("word,ipa\ncat,kæt\n")
    supplied = {}

    def backend(**kwargs):
        supplied.update(kwargs)
        return fake_backend

    monkeypatch.setattr(ba, "PhoneticXeusBackend", backend)
    result = CliRunner().invoke(
        app, ["phonetic", str(transcript), "--pronunciations", str(path)]
    )
    assert result.exit_code == 0, result.output
    assert supplied["pronunciations"] == {"cat": "kæt"}


@pytest.mark.parametrize(
    "language,word,overrides,observed,expected",
    [("eng", "cat", {"cat": "kæt"}, "<blank>/kʰ/æ̃/t", "kʰæ̃t"),
     ("rus", "кот", None, "<blank>/k/o/t", "kot")],
)
def test_backend_resamples_and_retains_phone_tokens(
    language, word, overrides, observed, expected
):
    from batchalign.backends.phonetic.xeus import PhoneticXeusBackend
    from batchalign._core.proto import PreparedAudio

    calls = []

    class Model:
        def transcribe(self, audio, sampling_rate):
            calls.append((len(audio), sampling_rate))
            return [{"predicted_transcript": observed}]

    backend = PhoneticXeusBackend(pronunciations=overrides)
    backend._model = Model()
    item = SimpleNamespace(
        source_id="sample",
        language=language,
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
                units=[SimpleNamespace(text=word, pause=False)],
            )
        ],
    )
    output = backend.call([item])
    assert calls == [(16000, 16000)]
    assert output[0].utterances[0].ipa == [expected]
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
