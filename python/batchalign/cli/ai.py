"""`ai` command - generic AI transcript editing over CHAT files."""

from __future__ import annotations

from enum import Enum
from pathlib import Path

import typer

from ._common import (
    collect_ai_inputs,
    write_outcome,
    CHAT_EXTENSIONS,
    resolve_inputs,
)
from ._options import cli_options
from .tui import Interface, Task


class AIEngine(str, Enum):
    """Generic AI backend selection."""

    dspy = "dspy"


def register(app: typer.Typer) -> None:
    @app.command()
    def ai(
        ctx: typer.Context,
        instruction: str = typer.Argument(
            ...,
            help="Instruction applied to every utterance.",
        ),
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
        engine: AIEngine = typer.Option(
            AIEngine.dspy,
            "--engine",
            case_sensitive=False,
        ),
        model: str = typer.Option(
            "zai-org/GLM-5.2",
            "--model",
            help="DSPy LM model string.",
        ),
        max_tokens: int = typer.Option(
            1024,
            "--max-tokens",
            min=1,
            help="Maximum output tokens for the DSPy LM call.",
        ),
        timeout: int = typer.Option(
            30,
            "--timeout",
            min=1,
            help="Per-utterance DSPy LM timeout in seconds.",
        ),
    ) -> None:
        """Run generic AI transcript editing."""
        import batchalign as ba

        selection = resolve_inputs(paths, input_list, CHAT_EXTENSIONS)
        opts = cli_options(ctx)

        with Interface.open(
            command="ai",
            params={"engine": engine.value, "model": model},
            output=out,
            verbosity=opts.verbosity,
            plain=opts.plain,
            quiet=opts.quiet,
        ) as ui:
            if engine is AIEngine.dspy:
                backend = ba.DspyAIBackend(
                    model="openai/"+model,
                    max_tokens=max_tokens,
                    timeout=timeout,
                )
            else:
                raise typer.BadParameter(f"unknown engine: {engine}")
            pipeline = ba.recipes.ai(ai_backend=backend, workers=opts.parallel)
            inputs, root = collect_ai_inputs(selection, instruction=instruction)
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
