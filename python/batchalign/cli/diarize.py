"""Standalone speaker diarization over existing timed CHAT transcripts."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

import typer

from ._common import (
    collect_chat_inputs,
    write_outcome,
    CHAT_EXTENSIONS,
    resolve_inputs,
)
from ._options import cli_options
from .tui import Interface, Task


class DiarizeEngine(str, Enum):
    """Speaker diarization backend exposed by the CLIs."""

    pyannote_ai = "pyannote-ai"
    pyannote = "pyannote"


def _build_backend(ba: Any, engine: DiarizeEngine, num_speakers: int) -> Any:
    if engine is DiarizeEngine.pyannote_ai:
        return ba.PyannoteAIBackend(num_speakers=num_speakers)
    return ba.PyannoteBackend(num_speakers=num_speakers)


def register(app: typer.Typer) -> None:
    @app.command()
    def diarize(
        ctx: typer.Context,
        paths: list[Path] | None = typer.Argument(
            None,
            exists=True,
            help="Timed CHAT file or folder to scan recursively; matching media is resolved from @Media or the transcript stem.",
        ),
        input_list: Path | None = typer.Option(
            None, "--input-list", "--file-list", "-i",
            exists=True, dir_okay=False,
            help="UTF-8 file listing input files or directories, one per line; relative to the list file.",
        ),
        out: Path | None = typer.Option(
            None,
            "--out",
            "-o",
            help="Optional output folder; if omitted, each source CHAT file is overwritten in place.",
        ),
        engine: DiarizeEngine = typer.Option(
            DiarizeEngine.pyannote_ai,
            "--engine",
            case_sensitive=False,
            help="Diarization engine: pyannote-ai (cloud) or pyannote (local).",
        ),
        num_speakers: int = typer.Option(
            0,
            "--num-speakers",
            "-n",
            min=0,
            help="Expected speaker count; zero auto-detects.",
        ),
    ) -> None:
        """Diarize timed CHAT and write speaker assignments back into CHAT."""
        import batchalign as ba

        selection = resolve_inputs(paths, input_list, CHAT_EXTENSIONS)
        opts = cli_options(ctx)

        with Interface.open(
            command="diarize",
            params={
                "engine": engine.value,
                "num_speakers": num_speakers or "auto",
            },
            output=out,
            verbosity=opts.verbosity,
            plain=opts.plain,
            quiet=opts.quiet,
        ) as ui:
            pipeline = ba.recipes.diarize(
                speaker_backend=_build_backend(ba, engine, num_speakers),
                workers=opts.parallel,
            )
            inputs, root = collect_chat_inputs(selection)
            for inp in inputs:
                ui.push(Task.from_input(inp))
            list(
                ui.run_pipeline(
                    pipeline,
                    inputs,
                    on_outcome=lambda outcome: write_outcome(
                        outcome, root, out
                    ),
                )
            )

        raise typer.Exit(code=ui.exit_code)


__all__ = ["DiarizeEngine", "_build_backend", "register"]
