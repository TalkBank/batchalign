"""`translate` command — emits CHAT with `%eng:` translation tiers."""

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


class TranslateEngine(str, Enum):
    """Translation backend selection (tbtbt-parity superset)."""

    google = "google"        # Google Cloud Translate / googletrans free fallback
    nllb = "nllb"            # facebook/nllb-200-distilled-1.3B local model
    tencent = "tencent"      # Tencent Cloud TMT (TextTranslate); does NOT support yue
    aliyun = "aliyun"        # Aliyun MT General; supports yue first-class


def register(app: typer.Typer) -> None:
    @app.command()
    def translate(
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
        target: str = typer.Option("eng", "--target", help="Target language code (ISO 639-3)."),
        engine: TranslateEngine = typer.Option(
            TranslateEngine.google,
            "--engine",
            case_sensitive=False,
        ),
    ) -> None:
        """Translate utterances; emits CHAT with `%eng:` tiers."""
        import batchalign as ba

        selection = resolve_inputs(paths, input_list, CHAT_EXTENSIONS)
        opts = cli_options(ctx)

        with Interface.open(
            command="translate",
            params={"engine": engine.value, "target": target},
            output=out,
            verbosity=opts.verbosity,
            plain=opts.plain,
            quiet=opts.quiet,
        ) as ui:
            backend: Any
            if engine is TranslateEngine.google:
                backend = ba.GoogleTranslateBackend(target=target)
            elif engine is TranslateEngine.nllb:
                backend = ba.NllbTranslateBackend(target=target)
            elif engine is TranslateEngine.tencent:
                backend = ba.TencentTmtBackend(target=target)
            elif engine is TranslateEngine.aliyun:
                backend = ba.AliyunTranslateBackend(target=target)
            else:
                raise typer.BadParameter(f"unknown engine: {engine}")
            pipeline = ba.recipes.translate(
                translate_backend=backend,
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
