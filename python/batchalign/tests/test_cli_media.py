"""Separate media hierarchies are paired at CLI input collection."""

from types import SimpleNamespace

import pytest
import typer
from typer.testing import CliRunner

from batchalign.cli import app
from batchalign.cli._common import CHAT_EXTENSIONS, attach_media, resolve_inputs


@pytest.mark.parametrize("command", [
    "align", "phonetic", "diarize", "morphotag", "translate", "utseg", "ai", "compare",
])
def test_transcript_commands_expose_media_option(command):
    result = CliRunner().invoke(app, [command, "--help"], color=False)
    assert result.exit_code == 0, result.output
    assert "--media" in result.output
    assert "-m" in result.output


@pytest.mark.parametrize("listed", [False, True])
def test_parallel_media_lookup_preserves_subfolders_and_source_ids(tmp_path, listed):
    transcripts = tmp_path / "transcripts"
    media = tmp_path / "media"
    sources, expected = [], []
    for name in ("a", "b"):
        folder = transcripts / name
        folder.mkdir(parents=True)
        source = folder / "clip.cha"
        source.write_text("@Media:\trecording.part, audio\n*PAR:\thello .\n")
        # A header match takes precedence over a transcript-stem match.
        media_folder = media / name
        media_folder.mkdir(parents=True)
        recording = media_folder / "recording.part.WaV"
        recording.touch()
        (media_folder / "clip.mp3").touch()
        sources.append(source)
        expected.append(recording)
    listing = tmp_path / "inputs.txt"
    listing.write_text("transcripts/a/clip.cha\ntranscripts/b/clip.cha\n")
    selection = resolve_inputs(None, listing, CHAT_EXTENSIONS) if listed else resolve_inputs(
        [transcripts], None, CHAT_EXTENSIONS
    )
    inputs = [SimpleNamespace(source_id=str(path), media=None) for path in sources]
    attach_media(inputs, selection, media)
    assert [inp.media for inp in inputs] == list(map(str, expected))
    assert [inp.source_id for inp in inputs] == list(map(str, sources))


def test_single_transcript_falls_back_to_stem_and_reports_missing_media(tmp_path):
    source = tmp_path / "clip.cha"
    source.write_text("@Media:\tmissing, audio\n")
    media = tmp_path / "media"
    media.mkdir()
    recording = media / "clip.wav"
    recording.touch()
    selection = resolve_inputs([source], None, CHAT_EXTENSIONS)
    inp = SimpleNamespace(source_id=str(source), media=None)
    attach_media([inp], selection, None)
    assert inp.media is None
    attach_media([inp], selection, media)
    assert inp.media == str(recording)
    recording.unlink()
    with pytest.raises(typer.BadParameter, match="no matching media for"):
        attach_media([inp], selection, media)


@pytest.mark.parametrize("kind", ["chat", "ai", "compare"])
def test_collectors_attach_media_to_each_input_type(tmp_path, kind):
    from batchalign.cli._common import collect_ai_inputs, collect_chat_inputs
    from batchalign.cli.compare import _pair_folder_with_gold

    source = tmp_path / "clip.cha"
    source.write_text("@Media:\trecording, audio\n")
    (tmp_path / "clip.gold.cha").touch()
    media = tmp_path / "media"
    media.mkdir()
    recording = media / "recording.wav"
    recording.touch()
    if kind == "ai":
        inputs, root = collect_ai_inputs(source, instruction="Fix punctuation", media=media)
        assert inputs[0].instruction == "Fix punctuation"
    elif kind == "compare":
        inputs, root = _pair_folder_with_gold(source, media=media)
        assert str(inputs[0].gold) == str(tmp_path / "clip.gold.cha")
    else:
        inputs, root = collect_chat_inputs(source, media=media)
    assert root == tmp_path
    assert str(inputs[0].source_id) == str(source)
    assert str(inputs[0].media) == str(recording)
