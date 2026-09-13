# Quick Start

**Status:** Current
**Last updated:** 2026-09-13

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

**Model downloads:** The first use of a backend may download its models. Download
size and startup time depend on the backend and language. Later runs reuse model
files from disk.

**Caching:** Batchalign saves text and audio backend results in a local LMDB
cache. Repeat runs can reuse matching results, although startup and file
processing still take time. See [Caching](caching.md) for details.

## Basic command shape

```bash
batchalign [GLOBAL OPTIONS] COMMAND [COMMAND OPTIONS] [PATHS...]
```

- Global options go before the command.
- Most processing commands use `-o/--out` for a destination directory.
- Omitting `-o/--out` means in-place processing when the command supports it.

## Transcribe audio to CHAT

```bash
batchalign transcribe ~/recordings/ -o ~/transcripts/ --lang eng
```

To use the local OpenAI Whisper package instead of the default Rev.AI engine:

```bash
batchalign transcribe ~/recordings/ -o ~/transcripts/ \
  --engine openai --lang eng
```

To use a local Whisper model:

```bash
batchalign transcribe ~/recordings/ -o ~/transcripts/ \
  --engine whisper --lang eng
```

## Align transcripts against audio

```bash
batchalign align ~/corpus/ -o ~/aligned/
```

Common useful flags:

```bash
batchalign align ~/corpus/ -o ~/aligned/ --engine whisper
batchalign align ~/corpus/ -o ~/aligned/ --utr-engine whisper
```

## Add morphosyntactic analysis

```bash
batchalign morphotag ~/corpus/ -o ~/tagged/
```

Useful variants:

```bash
batchalign morphotag ~/corpus/ -o ~/tagged/ --retokenize
batchalign morphotag ~/corpus/ -o ~/tagged/ --keep-existing
```

## Verbosity

```bash
batchalign align ~/corpus/ -o ~/aligned/
batchalign -v align ~/corpus/ -o ~/aligned/
batchalign -vv align ~/corpus/ -o ~/aligned/
batchalign -vvv align ~/corpus/ -o ~/aligned/
```

## Next steps

- [Batchalign Desktop (Experimental)](desktop-app.md) — in-repo GUI shell status and scope
- [CLI Reference](cli-reference.md)
- [Performance](performance.md)
- [Rev.AI Integration](rev-ai.md)
- [Python API](python-api.md)
