# Batchalign

**Status:** Current
**Last updated:** 2026-09-07

This repository contains [Batchalign](https://github.com/TalkBank/batchalign):
the audio and ML pipeline for producing and enriching CHAT transcripts. It
supports transcription, forced alignment, morphotagging, utterance
segmentation, translation, diarization, comparison, and the Batchalign desktop
shell.

## Install Batchalign

On macOS or Linux:

```bash
curl -LsSf https://raw.githubusercontent.com/TalkBank/batchalign/main/bootstrap/bootstrap.sh | sh
```

On Windows, from PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-Expression ((Invoke-WebRequest -UseBasicParsing 'https://raw.githubusercontent.com/TalkBank/batchalign/main/bootstrap/bootstrap.ps1').Content)"
```

The bootstrapper installs [uv](https://docs.astral.sh/uv/getting-started/installation/)
when needed, then installs or upgrades `batchalign[all]` on Python 3.11 with
prerelease versions enabled. The installer requires Batchalign 0.10 or newer.

Next, follow the [Quick Start](book/src/batchalign/user-guide/quick-start.md).
If anything is confusing, see the [Batchalign documentation](book/src/batchalign/introduction.md).

The CHAT parser, typed model, transformations, and grammar come from the
version-pinned [TalkBank Chatter repository](https://github.com/TalkBank/chatter).
They are dependencies of Batchalign rather than separately shipped products in
this repository.

## Development

Use the Bazel-backed `just` recipes:

```bash
just batchalign build debug
just batchalign test debug
just batchalign pytest
just batchalign cli -- --help
```

`just batchalign cli` is the authoritative development entrypoint for the CLI.
Bazel uses host-adaptive parallelism by default. Set `BATCHALIGN_BAZEL_JOBS`
explicitly when a resource-constrained runner needs a lower limit.

The main source areas are:

- `crates/batchalign/` — typed Rust core and PyO3 engine
- `python/batchalign/` — Python backends and CLI
- `apps/batchalign/` — desktop application
- `resources/test_fixtures/` — integration and parity fixtures
- `scripts/parity/` — bounded pre/post parity tooling

## License

BSD-3-Clause. Copyright (c) 2026, Carnegie Mellon University.
