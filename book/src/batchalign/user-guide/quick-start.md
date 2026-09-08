# Quick Start

**Status:** Current
**Last updated:** 2026-09-07

Install Batchalign with the command in the
[TalkBank/batchalign README](https://github.com/TalkBank/batchalign#install-batchalign).

## 1. Open a command window

- **macOS:** Open Terminal. [Apple explains where to find it](https://support.apple.com/guide/terminal/apd5265185d-f365-44cb-8b09-71a064a42125/mac).
- **Windows:** Open the Start menu, type `PowerShell`, and select PowerShell.
  [Microsoft's PowerShell guide includes startup help](https://learn.microsoft.com/powershell/scripting/learn/ps101/01-getting-started).
- **Linux:** Open the Terminal application from your applications menu. On
  many systems, Ctrl-Alt-T opens it directly.

## 2. Check the installation

Paste this command and press Enter:

```bash
batchalign --help
```

If Batchalign prints a list of commands, it is ready.

## 3. Process a file or folder

This example adds `%mor` and `%gra` tiers to every CHAT file in a folder:

```bash
batchalign morphotag "/Users/me/Documents/My Corpus"
```

In PowerShell, a Windows path looks like this:

```powershell
batchalign morphotag "C:\Users\me\Documents\My Corpus"
```

Batchalign accepts either one CHAT file or a folder. Use quotation marks around
paths containing spaces. Unless you specify an output folder, `morphotag`
updates the files in place.

## Before you start

**Model downloads:** The first time you run a processing command, Batchalign
downloads ML models (~2 GB). This is a one-time cost — subsequent runs use
cached models from disk.

**Caching:** Batchalign caches **audio-bound** intermediate results
(forced-alignment word timings and the UTR ASR pass) in a local SQLite
database, so re-running `align` or `transcribe` on the same audio
returns those steps from cache. Text-NLP commands (`morphotag`,
`utseg`, `translate`, `coref`) are not cached and always recompute.
See [Caching](caching.md) for details.

**Performance:** Back-to-back runs are still much faster than first-run model
downloads because models and caches stay on disk. If you need hot in-memory
workers across repeated runs, start an explicit server with `batchalign serve`.
See [Performance](performance.md) for tuning tips.

## Basic command shape

```bash
batchalign [GLOBAL OPTIONS] COMMAND [COMMAND OPTIONS] [PATHS...]
```

- Global options go before the command.
- Most processing commands use `-o/--output` for a destination directory.
- Omitting `-o/--output` means in-place processing when the command supports it.

## Transcribe audio to CHAT

```bash
batchalign transcribe ~/recordings/ -o ~/transcripts/ --lang eng
```

To use OpenAI Whisper instead of the default Rev.AI engine:

```bash
batchalign transcribe ~/recordings/ -o ~/transcripts/ \
  --asr-engine whisper-oai --lang eng
```

To use a local Whisper model:

```bash
batchalign transcribe ~/recordings/ -o ~/transcripts/ \
  --asr-engine whisper --lang eng
```

Important routing note: explicit `--server` now submits shared-filesystem
`paths_mode` jobs for `transcribe`. The target server must be able to read the
same input paths and write the requested output paths.

## Align transcripts against audio

```bash
batchalign align ~/corpus/ -o ~/aligned/
```

Common useful flags:

```bash
batchalign align ~/corpus/ -o ~/aligned/ --wor
batchalign align ~/corpus/ -o ~/aligned/ --fa-engine whisper
batchalign align ~/corpus/ -o ~/aligned/ --utr-engine whisper
```

## Add morphosyntactic analysis

```bash
batchalign morphotag ~/corpus/ -o ~/tagged/
```

Useful variants:

```bash
batchalign morphotag ~/corpus/ -o ~/tagged/ --retokenize
batchalign morphotag ~/corpus/ -o ~/tagged/ --skipmultilang
```

`morphotag` is not cached, so repeated runs run the full Stanza pipeline
again. The wall-clock win for repeated runs comes from keeping workers
warm in memory rather than from disk caching. For interactive sessions
where you want workers to stay loaded across commands, use explicit
server mode (`batchalign serve start` plus `--server`).

## Verbosity

```bash
batchalign align ~/corpus/ -o ~/aligned/
batchalign -v align ~/corpus/ -o ~/aligned/
batchalign -vv align ~/corpus/ -o ~/aligned/
batchalign -vvv align ~/corpus/ -o ~/aligned/
```

## Run logs

```bash
batchalign logs
batchalign logs --last
batchalign logs --export
batchalign logs --clear
```

## Remote server mode

For commands that support explicit remote dispatch:

```bash
batchalign --server http://yourserver:8000 morphotag ~/corpus/ -o ~/tagged/
batchalign --server http://yourserver:8000 align ~/corpus/ -o ~/aligned/
```

## Next steps

- [Batchalign Desktop (Experimental)](desktop-app.md) — in-repo GUI shell status and scope
- [CLI Reference](cli-reference.md)
- [Performance](performance.md)
- [Server Mode](server-mode.md)
- [Rev.AI Integration](rev-ai.md)
- [Python API](python-api.md)
