"""`utseg` command — utterance segmentation over CHAT files."""

from __future__ import annotations

from pathlib import Path

import typer

from ._common import (
    collect_chat_inputs,
    write_outcome,
    CHAT_EXTENSIONS,
    resolve_inputs,
)
from ._options import cli_options, inference_device
from .tui import Interface, Task


def register(app: typer.Typer) -> None:
    @app.command()
    def utseg(
        ctx: typer.Context,
        paths: list[Path] | None = typer.Argument(
            None,
            exists=True,
            help="Input CHAT files or directories to walk recursively.",
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
            help="Optional output folder; if omitted, each source file is overwritten in place.",
        ),
        stanza_fallback: bool = typer.Option(False, "--stanza-fallback/--no-stanza-fallback"),
        language: str = typer.Option("en", "--language"),
        force_cpu: bool = typer.Option(
            False,
            "--force-cpu",
            help="Run utterance segmentation on CPU.",
        ),
        allow_mps: bool = typer.Option(
            False,
            "--allow-mps",
            help="Use Apple MPS for utterance segmentation when available.",
        ),
    ) -> None:
        """Utterance segmentation pass over CHAT."""
        import batchalign as ba

        selection = resolve_inputs(paths, input_list, CHAT_EXTENSIONS)
        opts = cli_options(ctx)
        device = inference_device(force_cpu=force_cpu, allow_mps=allow_mps)

        with Interface.open(
            command="utseg",
            params={
                "lang": language,
                "stanza_fallback": stanza_fallback,
                "device": device or "auto",
            },
            output=out,
            verbosity=opts.verbosity,
            plain=opts.plain,
            quiet=opts.quiet,
        ) as ui:
            # `--language` is the typer-side ISO-2 alias; the backend pin
            # uses ISO-3. The model registry covers eng/yue (BA2 parity);
            # extend `_UTTERANCE_RESOLVE` in `chatutterance.py` if more
            # languages are added.
            lang3 = {"en": "eng", "yue": "yue", "zh-yue": "yue"}.get(language, language)
            # `stanza_fallback` is a recipe knob currently inert for the
            # BERT/CHATUtterance backend — the flag stays in the typer
            # surface for forward compat with a future stanza-based
            # fallback path.
            _ = stanza_fallback
            pipeline = ba.recipes.utseg(
                utseg_backend=ba.CHATUtteranceBackend(
                    lang=lang3,
                    device=device,
                ),
                workers=opts.parallel,
            )
            inputs, root = collect_chat_inputs(selection)
            for inp in inputs:
                ui.push(Task.from_input(inp))
            list(
                ui.run_pipeline(
                    pipeline,
                    inputs,
                    on_outcome=lambda outcome: write_outcome(outcome, root, out),
                )
            )

        raise typer.Exit(code=ui.exit_code)
