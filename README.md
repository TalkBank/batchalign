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

## Website and book

The website is an mdBook. Edit the homepage in `book/src/index.md`, the other
pages in `book/src/`, and navigation in `book/src/SUMMARY.md`.

```bash
just docs setup       # once: install mdBook and its plugins; requires Rust/Cargo
just docs serve       # http://localhost:3000/; automatically reloads edits
# Or choose another port: just docs serve 8000
```

`just docs build` builds the website into `book/build/html/`.
Live previews use separate `book/build/preview-<port>/` directories, so builds
and previews can run at the same time.
The docs workflow checks pull requests and deploys that directory on pushes to
`main`. Enable **Settings → Pages → Build and deployment → Source: GitHub
Actions** once in the repository before deploying.

The homepage loads `book/src/downloads.js` and shows macOS, Windows, and Linux
download buttons. It scans published stable releases, falling back to older
releases when necessary. macOS links to a DMG, Windows to an x86-64 installer,
and Linux offers only x86-64 DEB and RPM packages. Other builds are available
through the all-releases link. Each main button shows its installer version.
Download URLs come from `assets[].browser_download_url`, so links update
without rebuilding the site. A manual releases link works when JavaScript or
the API is unavailable. To inspect the latest tag yourself:

```bash
curl -fsSL https://api.github.com/repos/TalkBank/batchalign/releases/latest | jq -r .tag_name
```

## License

BSD-3-Clause. Copyright (c) 2026, Carnegie Mellon University.
