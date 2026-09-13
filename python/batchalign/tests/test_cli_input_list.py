"""Input lists and positional paths share discovery and output semantics."""

from importlib import import_module
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from batchalign.cli import app
from batchalign.cli._common import CHAT_EXTENSIONS, resolve_inputs, write_outcome

COMMANDS = [
    "transcribe", "align", "morphotag", "translate", "ai",
    "utseg", "compare", "convert", "diarize",
]


def test_list_matches_positional_paths_and_deduplicates(tmp_path):
    folder = tmp_path / "with spaces"
    nested = folder / "nested"
    nested.mkdir(parents=True)
    first = folder / "first.cha"
    second = nested / "second.cha"
    first.write_text("first")
    second.write_text("second")
    (folder / "ignored.wav").write_bytes(b"media")
    listing = tmp_path / "inputs.txt"
    listing.write_text("\ufeff# comment\n\nwith spaces\nwith spaces/first.cha\n")
    selected = resolve_inputs(None, listing, CHAT_EXTENSIONS)
    assert selected == resolve_inputs([folder, first], None, CHAT_EXTENSIONS)
    assert set(selected.paths) == {first, second}
    assert selected.root == folder
    assert resolve_inputs([second], listing, CHAT_EXTENSIONS).paths.count(second) == 1


def test_list_paths_are_relative_to_list_not_cwd(tmp_path, monkeypatch):
    source = tmp_path / "test.cha"
    source.touch()
    listing = tmp_path / "inputs.txt"
    listing.write_text(f"test.cha\n{source}\n")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    assert resolve_inputs(None, listing, CHAT_EXTENSIONS).paths == (source,)


def test_missing_list_entry_reports_line(tmp_path):
    listing = tmp_path / "inputs.txt"
    listing.write_text("# comment\nmissing.cha\n")
    with pytest.raises(typer.BadParameter, match=r"inputs.txt:2: input path does not exist"):
        resolve_inputs(None, listing, CHAT_EXTENSIONS)


def test_empty_list_requires_input(tmp_path):
    listing = tmp_path / "inputs.txt"
    listing.write_text("\n# comment\n")
    with pytest.raises(typer.BadParameter, match="provide input paths"):
        resolve_inputs(None, listing, CHAT_EXTENSIONS)


def test_list_output_layout_and_sibling_writes(tmp_path):
    sources = []
    for name in ("a", "b"):
        folder = tmp_path / name
        folder.mkdir()
        source = folder / "clip.cha"
        source.touch()
        sources.append(source)
    listing = tmp_path / "inputs.txt"
    listing.write_text("a/clip.cha\nb/clip.cha\n")
    selection = resolve_inputs(None, listing, CHAT_EXTENSIONS)
    assert selection.root == tmp_path
    written = []

    class Outcome:
        def __init__(self, source):
            self.source_id = str(source)

        def write(self, target, **kwargs):
            written.append(Path(target))

    for source in selection.paths:
        write_outcome(Outcome(source), selection.root, tmp_path / "out")
        write_outcome(Outcome(source), selection.root, None)
    assert written == [tmp_path / "out/a/clip.cha", sources[0],
                       tmp_path / "out/b/clip.cha", sources[1]]


@pytest.mark.parametrize("command", COMMANDS)
@pytest.mark.parametrize("mode", ["list", "positional"])
def test_every_processing_command_resolves_multiple_inputs(tmp_path, monkeypatch, command, mode):
    suffix = ".wav" if command in ("transcribe", "convert") else ".cha"
    first = tmp_path / f"first{suffix}"
    first.touch()
    folder = tmp_path / "folder"
    folder.mkdir()
    second = folder / f"second{suffix}"
    second.touch()
    listing = tmp_path / "inputs.txt"
    listing.write_text(f"{first.name}\nfolder\n")
    captured = []

    def resolve_and_stop(paths, input_list, suffixes):
        captured.append(resolve_inputs(paths, input_list, suffixes))
        # Stop before any model or credentials are required.
        raise typer.Exit(0)

    monkeypatch.setattr(import_module(f"batchalign.cli.{command}"), "resolve_inputs", resolve_and_stop)
    args = [command]
    if command == "transcribe":
        args.extend(["--lang", "eng"])
    if command == "ai":
        args.append("Fix punctuation")
    if command == "convert":
        args.extend(["--format", "mp3"])
    args.extend(["-i", str(listing)] if mode == "list" else [str(first), str(folder)])
    result = CliRunner().invoke(app, args)
    assert result.exit_code == 0, (result.output, result.exception)
    assert set(captured[0].paths) == {first, second}


def test_alignment_language_lookup_uses_list(tmp_path):
    from batchalign.cli.align import _infer_lang

    source = tmp_path / "spanish.cha"
    source.write_text("@Languages:\tspa\n")
    selection = resolve_inputs([source], None, CHAT_EXTENSIONS)
    assert _infer_lang(selection).alpha_3 == "spa"


def test_compare_pairs_gold_beside_each_listed_file(tmp_path, monkeypatch):
    from batchalign.cli.compare import _pair_folder_with_gold

    source = tmp_path / "test.cha"
    gold = tmp_path / "test.gold.cha"
    source.touch()
    gold.touch()
    monkeypatch.setattr("batchalign.inputs.paired_from_paths", lambda main, gold, **kw: (main, gold))
    selection = resolve_inputs([tmp_path], None, CHAT_EXTENSIONS)
    inputs, root = _pair_folder_with_gold(selection)
    assert inputs == [(str(source), str(gold))]
    assert root == tmp_path
