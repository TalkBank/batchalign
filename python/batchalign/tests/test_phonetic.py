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


@pytest.mark.parametrize(
    "phones,reference,expected",
    [
        (["k", "æ", "t"], ["ðə", "kæt"], ["…", "kæt"]),
        (["k", "æ", "t"], ["kæt", "ðə"], ["kæt", "…"]),
        (["k", "æ", "t", "d", "ɒ", "ɡ"], ["kæt", "ə", "dɒɡ"], ["kæt", "…", "dɒɡ"]),
        ([], ["kæt", "dɒɡ"], ["…", "…"]),
        # Actual Xeus output for "just to test batch line", 5305–6555 ms.
        (["t", "ʃ", "ɪ", "s", "t", "æ", "z", "æ", "s", "p", "æ", "ʃ", "ə", "l", "a", "ɪ̃", "n"],
         ["dʒˈʌst", "tuː", "tˈɛst", "bˈætʃ", "lˈaɪn"],
         ["…", "tʃ", "ɪst", "æzæspæʃə", "laɪ̃n"]),
    ],
)
def test_projection_marks_unresolved_units(phones, reference, expected):
    assert project_phones(phones, reference) == expected
    assert "".join(unit for unit in expected if unit != "…") == "".join(phones)


@pytest.mark.parametrize("phones,reference", [(["k"], []), (["k"], [""]), ([""], ["k"])])
def test_projection_still_rejects_invalid_input(phones, reference):
    with pytest.raises(ValueError):
        project_phones(phones, reference)


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
        phone = "tə"

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
                        unit.text if unit.pause else self.phone for unit in utterance.units
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


@pytest.mark.parametrize("phone", ["tə", "…"])
@pytest.mark.parametrize("language", ["eng", "fra", "rus"])
def test_cli_runner_writes_pho_and_preserves_existing(
    transcript, fake_backend, tmp_path, language, phone
):
    fake_backend.phone = phone
    transcript.write_text(transcript.read_text().replace("eng", language))
    output = tmp_path / "out"
    result = CliRunner().invoke(
        app, ["phonetic", str(transcript), "--out", str(output)]
    )
    assert result.exit_code == 0, result.output
    text = (output / transcript.name).read_text()
    assert f"%pho:\t{phone} (.) {phone}" in text
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
     ("eng", "cat", {"cat": "kæt"}, "<blank>", "…"),
     ("rus", "кот", None, "<blank>/k/o/t", "kot")],
)
def test_backend_resamples_and_retains_phone_tokens(
    language, word, overrides, observed, expected, caplog, monkeypatch
):
    from batchalign.backends.phonetic.xeus import PhoneticXeusBackend
    from batchalign._core.proto import PreparedAudio

    calls = []

    def transcribe(model, audio_batch):
        calls.extend((len(audio), 16000) for audio in audio_batch)
        return [[p for p in observed.split("/") if p != "<blank>"]]

    monkeypatch.setattr("batchalign.backends.phonetic.xeus.transcribe_batch", transcribe)

    backend = PhoneticXeusBackend(pronunciations=overrides)
    backend._model = object()
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
    if expected == "…":
        assert "sample: phonetic 0–1000 ms: no phones aligned to ['cat']" in caplog.text
    else:
        assert "no phones aligned" not in caplog.text
    item.utterances[0].end_ms = 2000
    with pytest.raises(ValueError, match="outside"):
        backend.call([item])


def test_backend_prepares_download_lock_before_inference(monkeypatch):
    """The download lock must exist before Textual redirects stderr."""
    from huggingface_hub.utils import tqdm
    from batchalign.backends.phonetic.xeus import PhoneticXeusBackend

    calls = []
    get_lock = tqdm.get_lock

    def prepare_lock():
        calls.append(get_lock())
        return calls[-1]

    monkeypatch.setattr(tqdm, "get_lock", prepare_lock)
    backend = PhoneticXeusBackend()
    assert len(calls) == 1
    assert backend._model is None


def test_backend_identity_tracks_pronunciations_and_pins_revision():
    from batchalign.backends.phonetic.xeus import PhoneticXeusBackend

    default = PhoneticXeusBackend()
    override = PhoneticXeusBackend(pronunciations={"cat": "kɛt"})
    assert default.name != override.name
    assert override.name == PhoneticXeusBackend(pronunciations={"cat": "kɛt"}).name
    assert default.name != PhoneticXeusBackend(batch_size=2).name
    with pytest.raises(ValueError, match="batch_size"):
        PhoneticXeusBackend(batch_size=0)
    with pytest.raises(ValueError, match="immutable"):
        PhoneticXeusBackend(revision="main")


def test_phonetic_grouping_matches_whisper_span_limit():
    from batchalign.backends.phonetic.utils.inference import group_utterances

    windows = [(0, 10000), (10000, 20000), (20000, 21000), (24001, 25000),
               (23000, 24000), (25000, 50000), (50000, 51000)]
    utterances = [SimpleNamespace(start_ms=start, end_ms=end) for start, end in windows]
    assert group_utterances(utterances) == [[0, 1], [2], [3], [4], [5], [6]]
    assert group_utterances([]) == []


def test_phonetic_padded_ctc_uses_lengths_and_independent_normalization():
    import torch
    from batchalign.backends.phonetic.utils.inference import transcribe_batch

    frontend = SimpleNamespace(normalize_audio=True)
    calls = []

    def encode(speech, lengths):
        assert not frontend.normalize_audio
        assert not torch.is_grad_enabled()
        calls.append((speech.clone(), lengths.tolist()))
        # A repeated phone across a blank must survive. The trailing b frames
        # in row 0 are padding and must NOT become an observed phone.
        ids = torch.tensor([[1, 1, 0, 1, 2, 2], [2, 2, 0, 2, 3, 0]])[:len(lengths)]
        logits = torch.nn.functional.one_hot(ids, num_classes=4).float()
        return (logits, []), torch.tensor([4, 6])[:len(lengths)]

    core = SimpleNamespace(
        frontend=frontend, encode=encode, blank_id=0,
        token_list=["<blank>", "a", "b", "<eos>"],
        ctc=SimpleNamespace(ctc_lo=lambda encoded: encoded),
    )
    model = SimpleNamespace(model=core, device="cpu", dtype=torch.float32)
    short = torch.tensor([1., 2., 3., 4.])
    long = torch.arange(8, dtype=torch.float32) * 100
    assert transcribe_batch(model, [short, long]) == [["a", "a"], ["b", "b"]]
    assert calls[0][1] == [4, 8]
    assert calls[0][0].shape == (2, 8)
    assert torch.equal(calls[0][0][0, 4:], torch.zeros(4))
    assert frontend.normalize_audio
    assert transcribe_batch(model, [short]) == [["a", "a"]]
    assert torch.equal(calls[0][0][0, :4], calls[1][0][0])

    def fail(*args):
        raise RuntimeError("encoder failed")

    core.encode = fail
    with pytest.raises(RuntimeError, match="encoder failed"):
        transcribe_batch(model, [short])
    assert frontend.normalize_audio


@pytest.mark.parametrize("batch_size", [None, 1, 2])
def test_phonetic_grouped_batches_restore_utterance_ownership(monkeypatch, batch_size):
    from batchalign.backends.phonetic.xeus import PhoneticXeusBackend
    from batchalign._core.proto import PreparedAudio

    def utterance(index, start, end, *words):
        return SimpleNamespace(
            index=index, start_ms=start, end_ms=end,
            units=[SimpleNamespace(text=word, pause=word == "(.)") for word in words],
        )

    item = SimpleNamespace(
        source_id="grouping", language="eng",
        audio=PreparedAudio(
            pcm_f32le=base64.b64encode(b"\x00" * 32000 * 4),
            sample_rate=1000, channels=1, frame_count=32000,
        ),
        utterances=[
            utterance(10, 0, 10000, "cat", "(.)"),
            utterance(20, 10000, 19000, "dog"),
            utterance(30, 21000, 22000, "fish"),
            utterance(40, 30000, 32000, "cat"),
        ],
    )
    backend = PhoneticXeusBackend(
        pronunciations={"cat": "kæt", "dog": "dɒɡ", "fish": "fɪʃ"},
        batch_size=batch_size, device="cpu",
    )
    backend._model = object()
    calls, ticks = [], []

    def transcribe(model, waves):
        lengths = [len(wave) for wave in waves]
        calls.append(lengths)
        phones = {16000: list("fɪʃ"), 32000: list("kæt"), 304000: list("kætdɒɡ")}
        return [phones[length] for length in lengths]

    monkeypatch.setattr("batchalign.backends.phonetic.xeus.transcribe_batch", transcribe)
    output = backend.call([item], progress=lambda *tick: ticks.append(tick))[0]
    if batch_size == 2:
        assert calls == [[16000, 32000], [304000]]
        assert ticks == [(2, 3), (3, 3)]
    else:
        assert calls == [[16000], [32000], [304000]]
        assert ticks == [(1, 3), (2, 3), (3, 3)]
    assert [result.index for result in output.utterances] == [10, 20, 30, 40]
    assert [result.ipa for result in output.utterances] == [["kæt", "(.)"], ["dɒɡ"], ["fɪʃ"], ["kæt"]]
