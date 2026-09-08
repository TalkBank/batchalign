from pathlib import Path

import pytest
import typer

from batchalign.cli._common import CHAT_EXTENSIONS, _walk, collect_chat_inputs
from batchalign.cli.align import _infer_lang


def test_align_language_inference_skips_appledouble_sidecar(tmp_path: Path) -> None:
    (tmp_path / "._session.cha").write_bytes(b"\x00\x05AppleDouble metadata")
    (tmp_path / "session.cha").write_text(
        "@UTF8\n@Begin\n@Languages:\teng\n*CHI:\thello .\n@End\n",
        encoding="utf-8",
    )

    assert [path.name for path in _walk(tmp_path, CHAT_EXTENSIONS)] == ["session.cha"]
    assert _infer_lang(tmp_path).alpha_3 == "eng"


def test_explicit_appledouble_sidecar_is_not_a_chat_input(tmp_path: Path) -> None:
    sidecar = tmp_path / "._session.cha"
    sidecar.write_bytes(b"\x00\x05AppleDouble metadata")

    assert _walk(sidecar, CHAT_EXTENSIONS) == []
    with pytest.raises(typer.BadParameter, match="no @Languages"):
        _infer_lang(sidecar)


def test_batch_discovery_schedules_largest_inputs_first(tmp_path: Path) -> None:
    (tmp_path / "a-small.cha").write_text("small", encoding="utf-8")
    (tmp_path / "z-large.cha").write_text("large transcript", encoding="utf-8")
    (tmp_path / "m-medium.cha").write_text("medium text", encoding="utf-8")

    assert [path.name for path in _walk(tmp_path, CHAT_EXTENSIONS)] == [
        "z-large.cha",
        "m-medium.cha",
        "a-small.cha",
    ]


def test_morphotag_discovery_groups_language_sets_without_losing_size_order(
    tmp_path: Path,
) -> None:
    fixtures = [
        ("large-english.cha", "eng", "one two three"),
        ("italian.cha", "ita", "uno"),
        ("small-english.cha", "eng", "one"),
        ("bilingual.cha", "spa, eng", "uno dos"),
    ]
    for name, languages, words in fixtures:
        (tmp_path / name).write_text(
            f"@UTF8\n@Languages:\t{languages}\n*CHI:\t{words} .\n",
            encoding="utf-8",
        )

    inputs, _ = collect_chat_inputs(tmp_path, group_by_language=True)

    assert [Path(item.path).name for item in inputs] == [
        "large-english.cha",
        "small-english.cha",
        "bilingual.cha",
        "italian.cha",
    ]
