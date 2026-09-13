"""`convert` command — convert supported media to WAV or MP3."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

import typer

from ._common import (
    MEDIA_EXTENSIONS,
    InputSelection,
    selected_inputs,
    safe_resolve,
    resolve_inputs,
)
from ._options import cli_options
from .tui import Interface, Task


class OutputFormat(str, Enum):
    mp3 = "mp3"
    wav = "wav"


def _target_for(source: Path, root: Path, out: Path | None, suffix: str) -> Path:
    if out is None:
        target = source.with_suffix(suffix)
    else:
        target = out / source.relative_to(root).with_suffix(suffix)
    # A same-format conversion beside the input needs a distinct name.
    if target.absolute() == source.absolute():
        target = target.with_name(f"{target.stem}.converted{suffix}")
    return target


def _collect(
    source: Path | InputSelection,
    out: Path | None,
    suffix: str,
) -> tuple[list[Any], Path, dict[str, Path]]:
    from batchalign.inputs import media_from_path

    selection = selected_inputs(source, MEDIA_EXTENSIONS)
    root = selection.root
    out_resolved = out.expanduser().resolve() if out is not None else None
    paths = []
    for path in selection.paths:
        resolved = path.resolve()
        if out_resolved is not None and resolved.is_relative_to(out_resolved):
            continue
        paths.append(path)
    if not paths:
        raise typer.BadParameter(f"no supported media files found in {source}")

    targets: dict[str, Path] = {}
    target_sources: dict[Path, Path] = {}
    for source in paths:
        target = _target_for(source, root, out, suffix)
        resolved_target = target.expanduser().resolve()
        resolved_source = source.resolve()
        if resolved_target == resolved_source:
            raise typer.BadParameter(f"conversion target would replace source media: {source}")
        if resolved_target in target_sources:
            other = target_sources[resolved_target]
            raise typer.BadParameter(
                f"multiple inputs map to {target}: {other} and {source}"
            )
        if target.exists():
            raise typer.BadParameter(f"conversion target already exists: {target}")
        if out_resolved is not None:
            target.parent.mkdir(parents=True, exist_ok=True)
            safe_resolve(target.parent, out_resolved)
        target_sources[resolved_target] = source
        targets[str(source)] = target

    inputs = [media_from_path(path, source_id=str(path)) for path in paths]
    return inputs, root, targets


def register(app: typer.Typer) -> None:
    @app.command()
    def convert(
        ctx: typer.Context,
        paths: list[Path] | None = typer.Argument(
            None,
            exists=True,
            help="Media file or folder to walk recursively.",
        ),
        format: OutputFormat = typer.Option(
            ...,
            "--format",
            case_sensitive=False,
            help="Output format: mp3 or wav.",
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
            help="Optional output folder; otherwise outputs are written beside each source.",
        ),
    ) -> None:
        """Convert media files to WAV or MP3 without replacing source media."""
        import batchalign as ba

        selection = resolve_inputs(paths, input_list, MEDIA_EXTENSIONS)
        opts = cli_options(ctx)
        suffix = f".{format.value}"
        inputs, _root, targets = _collect(selection, out, suffix)

        with Interface.open(
            command="convert",
            params={"format": format.value},
            output=out,
            verbosity=opts.verbosity,
            plain=opts.plain,
            quiet=opts.quiet,
        ) as ui:
            pipeline = ba.recipes.convert(format=format.value, workers=opts.parallel)
            for inp in inputs:
                ui.push(Task.from_input(inp))

            def write_output(outcome: Any) -> None:
                target = targets[str(outcome.source_id)]
                target.parent.mkdir(parents=True, exist_ok=True)
                outcome.write(str(target))

            list(ui.run_pipeline(pipeline, inputs, on_outcome=write_output))

        raise typer.Exit(code=ui.exit_code)
