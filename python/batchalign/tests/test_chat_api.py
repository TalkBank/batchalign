"""Public CHAT API contracts across the Python/Rust boundary."""

import io

import pytest

from batchalign.chat import CHATFile, Media, Speaker, Utterance


@pytest.fixture
def child():
    return Speaker("CHI", language="eng", corpus="test", role="Target_Child", name="Sam")


@pytest.fixture
def source():
    return (
        "@UTF8\n@Begin\n@Languages:\teng, fra\n"
        "@Participants:\tCHI Sam Target_Child, MOT Mother\n"
        "@ID:\teng,fra|test|CHI|2;03.04|female|group||Target_Child|school|custom|\n"
        "@ID:\teng|test|MOT|||||Mother|||\n"
        "@Media:\tsample, audio\n@Date:\t12-OCT-2026\n"
        "*CHI:\tthe cat . \x150_1000\x15\n%pho:\tðə kæt\n"
        "@Comment:\tkeep this here\n*MOT:\thello . \x151000_2000\x15\n@End\n"
    )


def test_new_and_serialization(child):
    chat = CHATFile.new()
    assert len(chat) == 0
    assert chat.speakers == chat.languages == chat.corpora == ()
    chat.utterances.append(Utterance(child, "I want a cookie ."))
    assert len(chat) == 1
    assert chat.speakers == (child,)
    assert chat.languages == ("eng",)
    assert chat.corpora == ("test",)
    text = chat.stringify()
    assert text == str(chat)
    assert "@Participants:\tCHI Sam Target_Child" in text
    assert "@ID:\teng|test|CHI|||||Target_Child|||" in text
    assert "\n\n" not in text
    assert CHATFile.parse(text).stringify() == text


def test_empty_document_roundtrip():
    chat = CHATFile.new()
    assert len(CHATFile.parse(str(chat))) == 0
    with pytest.raises(ValueError):
        CHATFile.parse("@UTF8\n@Begin\n@Languages:\tinvalid\n@End\n")


def test_public_reexports():
    import batchalign as ba

    from batchalign.backends import Speaker as SpeakerBackend

    assert (ba.CHATFile, ba.Media, ba.Utterance) == (CHATFile, Media, Utterance)
    assert ba.chat.Speaker is Speaker
    assert ba.Speaker is SpeakerBackend


def test_explicit_utterance_languages_are_derived(source):
    source = source.replace("eng,fra|test|CHI", "eng|test|CHI")
    source = source.replace("the cat .", "[- fra] le chat .")
    chat = CHATFile.parse(source)
    assert chat.languages == ("eng", "fra")
    assert "@Languages:\teng, fra" in str(chat)
    assert CHATFile.parse(str(chat)).stringify() == str(chat)


def test_reordered_speakers_preserve_the_original_utterance_language():
    source = (
        "@UTF8\n@Begin\n@Languages:\teng, fra\n"
        "@Participants:\tMOT Mother\n@ID:\tfra|test|MOT|||||Mother|||\n"
        "*MOT:\tcat .\n@End\n"
    )
    chat = CHATFile.parse(source)
    assert chat.languages == ("fra", "eng")
    assert "[- eng]" in str(chat)
    assert CHATFile.parse(str(chat)).stringify() == str(chat)


def test_media_is_typed_and_roundtrips(child, source):
    chat = CHATFile.new()
    media = Media("sample", media_type="audio")
    assert chat.media is None
    chat.media = media
    assert chat.media == media
    chat.utterances.append(Utterance(child, "cat .", timing=(0, 1000)))
    assert CHATFile.parse(str(chat)).media == media
    chat.media = Media("movie", media_type="video", status="missing")
    assert "@Media:\tmovie, video, missing" in str(chat)
    assert chat.media.filename == "movie"
    assert chat.media.media_type == "video"
    assert chat.media.status == "missing"
    with pytest.raises(TypeError):
        chat.media = "sample"
    with pytest.raises(AttributeError):
        chat.media.filename = "changed"
    chat.media = None
    assert chat.media is None
    with pytest.raises(ValueError, match="E752"):
        str(chat)
    chat.utterances[0].timing = None
    assert "@Media:" not in str(chat)
    parsed = CHATFile.parse(source)
    assert parsed.media == media
    parsed.media = Media("replacement")
    assert str(parsed).count("@Media:") == 1


@pytest.mark.parametrize("arguments", [
    dict(filename="bad,name"), dict(filename=""),
    dict(filename="sample", media_type="movie"),
    dict(filename="sample", status="invalid"),
])
def test_media_rejects_invalid_values(arguments):
    with pytest.raises(ValueError):
        Media(**arguments)


def test_dependent_tiers_validate_in_their_full_context(child):
    utterance = Utterance(child, "cat .")
    utterance.tiers["mor"] = "n|cat ."
    utterance.tiers["gra"] = "1|0|ROOT 2|1|PUNCT"
    assert utterance.tiers["mor"] == "n|cat ."
    assert utterance.tiers["gra"] == "1|0|ROOT 2|1|PUNCT"
    with pytest.raises(ValueError):
        del utterance.tiers["mor"]
    assert tuple(utterance.tiers) == ("mor", "gra")
    del utterance.tiers["gra"]
    del utterance.tiers["mor"]


@pytest.mark.parametrize("lines", [False, True])
@pytest.mark.parametrize("keepends", [False, True])
def test_parse_and_read_preserve_metadata_and_headers(source, lines, keepends):
    chat = CHATFile.parse(source.splitlines(keepends=keepends) if lines else source)
    assert len(chat) == 2
    assert chat.languages == ("eng", "fra")
    assert chat.corpora == ("test",)
    first, second = chat.utterances
    assert first.speaker.code == "CHI"
    assert first.speaker.name == "Sam"
    assert first.speaker.languages == ("eng", "fra")
    assert first.words == ("the", "cat")
    assert first.tiers["pho"] == "ðə kæt"
    assert first.timing == (0, 1000)
    text = chat.stringify()
    assert "2;03.04|female|group||Target_Child|school|custom|" in text
    assert "@Date:\t12-OCT-2026" in text
    assert text.index("*CHI:") < text.index("@Comment:") < text.index("*MOT:")
    assert CHATFile.read(io.StringIO(text)).stringify() == text
    output = io.StringIO()
    chat.write(output)
    assert output.getvalue() == text
    assert not output.closed
    assert second.speaker.role == "Mother"


def test_live_utterance_edits_and_detached_handles(child):
    chat = CHATFile.new()
    original = Utterance(child, "cat .")
    chat.utterances.append(original)
    original.text = "dog ."
    assert chat.utterances[0] is original
    assert "dog ." in str(chat)
    chat.utterances.insert(0, Utterance(child, "bird ."))
    assert chat.utterances[-1] is original
    assert chat.utterances[:] == list(chat.utterances)
    assert chat.utterances.pop() is original
    original.text = "fish ."
    assert "fish" not in str(chat)
    chat.utterances[0] = original
    assert "fish ." in str(chat)
    del chat.utterances[-1]
    assert len(chat) == 0
    assert chat.speakers == chat.languages == chat.corpora == ()


def test_metadata_is_derived_and_immutable(child):
    chat = CHATFile.new()
    chat.utterances.append(Utterance(child, "cat ."))
    for name in ["speakers", "languages", "corpora"]:
        with pytest.raises(AttributeError):
            setattr(chat, name, ())
        with pytest.raises(TypeError):
            getattr(chat, name)[0] = "changed"
    for name, value in [("code", "MOT"), ("corpus", "other"), ("languages", ("fra",))]:
        with pytest.raises(AttributeError):
            setattr(chat.speakers[0], name, value)
    mother = Speaker("MOT", language="fra", corpus="other", role="Mother")
    chat.utterances[0].speaker = mother
    assert chat.speakers == (mother,)
    assert chat.languages == ("fra",)
    assert chat.corpora == ("other",)
    assert "*MOT:\tcat ." in str(chat)


def test_tier_and_timing_edits_are_atomic(source):
    chat = CHATFile.parse(source)
    utterance = chat.utterances[0]
    tiers = utterance.tiers
    tiers["pho"] = "tə kʰæt"
    tiers["com"] = "a note"
    assert tuple(tiers) == ("pho", "com")
    assert len(tiers) == 2
    before = str(chat)
    with pytest.raises(ValueError):
        tiers["pho"] = "one"
    assert str(chat) == before
    with pytest.raises(ValueError):
        utterance.text = "one two three ."
    assert str(chat) == before
    with pytest.raises(ValueError):
        utterance.timing = (1000, 1000)
    assert str(chat) == before
    utterance.timing = (100, 900)
    assert utterance.timing == (100, 900)
    del tiers["pho"]
    utterance.text = "one two three ."
    assert utterance.words == ("one", "two", "three")
    utterance.timing = None
    assert utterance.timing is None
    with pytest.raises(KeyError):
        tiers["pho"]
    assert CHATFile.parse(str(chat)).stringify() == str(chat)


def test_silent_participants_are_not_exposed(source):
    chat = CHATFile.parse(source.replace("*MOT:\thello . \x151000_2000\x15\n", ""))
    assert [speaker.code for speaker in chat.speakers] == ["CHI"]
    assert "@ID:\teng|test|MOT" not in str(chat)


def test_conflicting_speaker_metadata_is_rejected_atomically(child):
    chat = CHATFile.new()
    chat.utterances.append(Utterance(child, "cat ."))
    conflicting = Utterance(Speaker("CHI", language="eng", corpus="other"), "dog .")
    for edit in [lambda: chat.utterances.append(conflicting),
                 lambda: chat.utterances.insert(0, conflicting)]:
        with pytest.raises(ValueError, match="conflicting metadata"):
            edit()
        assert len(chat) == 1
        assert chat.corpora == ("test",)


def test_conflicting_collection_replacement_keeps_the_original(child):
    chat = CHATFile.new()
    chat.utterances.append(Utterance(child, "cat ."))
    original = Utterance(child, "dog .")
    chat.utterances.append(original)
    replacement = Utterance(Speaker("CHI", language="eng", corpus="other"), "bird .")
    with pytest.raises(ValueError):
        chat.utterances[1] = replacement
    assert chat.utterances[1] is original
    assert chat.corpora == ("test",)


def test_invalid_document_write_does_not_modify_the_stream(child):
    chat = CHATFile.new()
    chat.utterances.append(Utterance(child, "cat .", timing=(0, 1000)))
    output = io.StringIO("original")
    with pytest.raises(ValueError):
        chat.write(output)
    assert output.getvalue() == "original"


@pytest.mark.parametrize("value", [None, 1, b"@Begin", [1], ("@Begin",)])
def test_parse_rejects_wrong_types(value):
    with pytest.raises(TypeError):
        CHATFile.parse(value)


def test_inputs_are_validated(child):
    with pytest.raises(ValueError):
        CHATFile.parse("this is not CHAT")
    for arguments in [dict(code="bad code", language="eng", corpus="test"),
                      dict(code="CHI", language="invalid", corpus="test"),
                      dict(code="CHI", language="eng", corpus=""),
                      dict(code="CHI", language="eng", corpus="test\n@End")]:
        with pytest.raises(ValueError):
            Speaker(**arguments)
    with pytest.raises(TypeError):
        Speaker("CHI", language="eng", corpus=5)
    with pytest.raises(TypeError):
        Utterance("CHI", "hello .")
    with pytest.raises(ValueError):
        Utterance(child, "29e .")
    with pytest.raises(ValueError):
        Utterance(child, "hello .\n*CHI:\tinjected .")
    chat = CHATFile.new()
    with pytest.raises(TypeError):
        chat.utterances.append("hello .")
    with pytest.raises(IndexError):
        chat.utterances.pop()
    utterance = Utterance(child, "cat .")
    with pytest.raises(TypeError):
        utterance.timing = "0_1000"
    with pytest.raises(OverflowError):
        utterance.timing = (-1, 1000)
