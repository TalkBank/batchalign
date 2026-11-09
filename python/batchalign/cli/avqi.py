"""Pair mirrored audio trees and collect acoustic measurements in avqi.csv."""

from __future__ import annotations

import csv
import os
import tempfile
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import typer

from ._common import MEDIA_EXTENSIONS
from ._options import cli_options
from .tui import Interface, Task

COLUMNS = [
    "source_id", "sv_file", "cs_file", "success", "error", "avqi",
    "cpps", "hnr", "shimmer_local", "shimmer_local_db", "slope", "tilt",
    "voiced_cs_duration", "sv_duration", "implementation",
]


@dataclass(frozen=True)
class AudioPair:
    key: str
    sustained_vowel: Path | None
    continuous_speech: Path | None


def _audio_tree(root: Path, role: str) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in MEDIA_EXTENSIONS:
            continue
        relative = path.relative_to(root).with_suffix("")
        stem = relative.name
        if stem.lower().endswith(f".{role}"):
            relative = relative.with_name(stem[:-len(role)-1])
        key = relative.as_posix()
        if key in result:
            raise typer.BadParameter(
                f"Ambiguous {role} pair {key!r}: {result[key]} and {path}"
            )
        result[key] = path.resolve()
    return result


def pair_audio(sustained_vowel: Path, continuous_speech: Path) -> list[AudioPair]:
    """Match relative stems, optionally stripping terminal .sv/.cs role markers."""
    if sustained_vowel.is_file() and continuous_speech.is_file():
        for path in (sustained_vowel, continuous_speech):
            if path.suffix.lower() not in MEDIA_EXTENSIONS:
                raise typer.BadParameter(f"Unsupported media extension: {path}")
        return [AudioPair(continuous_speech.stem, sustained_vowel.resolve(), continuous_speech.resolve())]
    if not sustained_vowel.is_dir() or not continuous_speech.is_dir():
        raise typer.BadParameter("Provide two audio files or two mirrored directories")
    with ThreadPoolExecutor(max_workers=2) as pool:
        vowels_future = pool.submit(_audio_tree, sustained_vowel, "sv")
        speech_future = pool.submit(_audio_tree, continuous_speech, "cs")
        vowels, speech = vowels_future.result(), speech_future.result()
    keys = sorted(vowels.keys() | speech.keys())
    if not keys:
        raise typer.BadParameter("No supported media found in either directory")
    return [AudioPair(key, vowels.get(key), speech.get(key)) for key in keys]


def _write_csv(path: Path, rows: list[dict]) -> None:
    """Publish only a complete CSV, and never leave an interrupted partial file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", newline="", encoding="utf-8", dir=path.parent,
            prefix=".avqi-", suffix=".csv", delete=False,
        ) as stream:
            temporary = Path(stream.name)
            writer = csv.DictWriter(stream, fieldnames=COLUMNS, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def register(app: typer.Typer) -> None:
    @app.command()
    def avqi(
        ctx: typer.Context,
        sustained_vowel: Path = typer.Argument(..., exists=True, help="Sustained-vowel file or directory."),
        continuous_speech: Path = typer.Argument(..., exists=True, help="Continuous-speech file or mirrored directory."),
        out: Path = typer.Option(Path("."), "--out", "-o", file_okay=False, help="Directory for avqi.csv."),
    ) -> None:
        """Calculate AVQI for paired recordings and write one avqi.csv.

        Directories pair by relative stem, allowing .sv/.cs markers and different
        audio extensions. Missing partners get failed rows. Both inputs need
        at least 20 kHz audio; sustained vowels need at least three seconds.
        Use the global --parallel option to control concurrent input processing.
        """
        import batchalign as ba

        pairs = pair_audio(sustained_vowel, continuous_speech)
        opts = cli_options(ctx)
        rows = {
            pair.key: dict(
                source_id=pair.key,
                sv_file=str(pair.sustained_vowel or ""),
                cs_file=str(pair.continuous_speech or ""),
                success=False, error="Processing did not complete",
            )
            for pair in pairs
        }
        with Interface.open(
            command="avqi", params={"engine": "praat"}, output=out,
            verbosity=opts.verbosity, plain=opts.plain, quiet=opts.quiet,
        ) as ui:
            inputs = []
            tasks = {}
            for pair in pairs:
                task = Task(source_id=pair.key, label=pair.key)
                tasks[pair.key] = task
                ui.push(task)
                if pair.sustained_vowel is None or pair.continuous_speech is None:
                    missing = "sustained vowel" if pair.sustained_vowel is None else "continuous speech"
                    message = f"Missing {missing} partner"
                    rows[pair.key]["error"] = message
                    task.fail(message)
                else:
                    inputs.append(ba.AvqiMediaInput(
                        sustained_vowel=pair.sustained_vowel,
                        continuous_speech=pair.continuous_speech,
                        source_id=pair.key,
                    ))
            if inputs:
                pipeline = ba.recipes.avqi(avqi_backend=ba.AvqiBackend(), workers=opts.parallel)

                def collect(outcome):
                    row = rows[str(outcome.source_id)]
                    if outcome.is_failed:
                        row.update(success=False, error=outcome.error)
                    else:
                        table = outcome.metrics
                        if table is None or len(table["rows"]) != 1:
                            raise ValueError("AVQI runner did not return one metrics row")
                        row.update(table["rows"][0]["columns"])
                        row.update(success=True, error="")

                list(ui.run_pipeline(pipeline, inputs, on_outcome=collect))
            # Input decoding can fail before the engine emits an outcome.
            # Those failures are delivered through the task callbacks instead.
            for key, task in tasks.items():
                if task.error:
                    rows[key].update(success=False, error=task.error)
            _write_csv(out / "avqi.csv", list(rows.values()))
        raise typer.Exit(code=ui.exit_code)
