"""Acoustic phonetic transcription of timed CHAT into `%pho`."""

from __future__ import annotations

from pathlib import Path

import typer

from ._common import CHAT_EXTENSIONS, collect_chat_inputs, resolve_inputs, write_outcome
from ._options import cli_options, inference_device
from .tui import Interface, Task


def register(app: typer.Typer) -> None:
    @app.command()
    def phonetic(
        ctx: typer.Context,
        paths: list[Path] | None = typer.Argument(
            None,
            exists=True,
            help="Timed CHAT files or directories with matching audio.",
        ),
        input_list: Path | None = typer.Option(
            None, "--input-list", "--file-list", "-i", exists=True, dir_okay=False
        ),
        out: Path | None = typer.Option(
            None, "--out", "-o", help="Output directory; defaults to writing in place."
        ),
        pronunciations: Path | None = typer.Option(
            None,
            "--pronunciations",
            exists=True,
            dir_okay=False,
            help="UTF-8 CSV overrides with header word,ipa and one word or CHAT unit "
            "per row. Example row: wug,wʌɡ. Replaces Epitran's pronunciation for that unit.",
        ),
        force_cpu: bool = typer.Option(False, "--force-cpu", help="Use CPU inference."),
    ) -> None:
        """Add observed IPA to `%pho`, preserving existing phonetic tiers.

        Requires utterance timing bullets (run utr first if absent).
        Reference IPA uses Epitran for the CHAT language; English requires Flite.

        Override example: --pronunciations pronunciations.csv

        CSV contents (header required):
        \b
        word,ipa
        wug,wʌɡ
        bonjour,bɔ̃ʒuʁ
        """
        import batchalign as ba
        from batchalign.backends.phonetic.utils.pronunciation import load_pronunciations

        selection = resolve_inputs(paths, input_list, CHAT_EXTENSIONS)
        opts = cli_options(ctx)
        overrides = None
        if pronunciations is not None:
            try:
                overrides = load_pronunciations(pronunciations)
            except (ValueError, OSError) as error:
                raise typer.BadParameter(
                    str(error), param_hint="--pronunciations"
                ) from error
        with Interface.open(
            command="phonetic",
            params={"engine": "phoneticxeus"},
            output=out,
            verbosity=opts.verbosity,
            plain=opts.plain,
            quiet=opts.quiet,
        ) as ui:
            backend = ba.PhoneticXeusBackend(
                device=inference_device(force_cpu=force_cpu, allow_mps=False),
                pronunciations=overrides,
            )
            pipeline = ba.recipes.phonetic(
                phonetic_backend=backend, workers=opts.parallel
            )
            inputs, root = collect_chat_inputs(selection)
            for item in inputs:
                ui.push(Task.from_input(item))
            list(
                ui.run_pipeline(
                    pipeline,
                    inputs,
                    on_outcome=lambda outcome: write_outcome(outcome, root, out),
                )
            )
        raise typer.Exit(code=ui.exit_code)
