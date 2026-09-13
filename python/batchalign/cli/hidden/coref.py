"""`coref` command — coreference resolution (stub, no backend bundled)."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from .._common import CHAT_EXTENSIONS, resolve_inputs


def register(app: typer.Typer) -> None:
    @app.command()
    def coref(
        paths: list[Path] | None = typer.Argument(
            None,
            exists=True,
            help="Folder to walk recursively for CHAT files (single file also accepted).",
        ),
        input_list: Path | None = typer.Option(
            None, "--input-list", "--file-list", "-i",
            exists=True, dir_okay=False,
            help="UTF-8 file listing input files or directories, one per line.",
        ),
        out: Path | None = typer.Option(
            None,
            "--out",
            "-o",
            help="Optional output folder; if omitted, each source file is overwritten in place.",
        ),
    ) -> None:
        """Coreference resolution (stub — wire a real coref backend)."""
        resolve_inputs(paths, input_list, CHAT_EXTENSIONS)
        c = Console()
        c.print("[red]fail[/]  coref: no backend shipped with this build")
        c.print("      [dim]hint:[/] use the Python API: "
                "`ba.recipes.coref(coref_backend=...)`")
        raise typer.Exit(code=2)
