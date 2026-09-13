# CLI reference

The `batchalign` and `batchalign3` entrypoints run the same CLI.
Options below are checked against `python/batchalign/cli/` for version 0.10.1.
Run `batchalign COMMAND --help` for the help shipped with your installation.

```text
batchalign [GLOBAL OPTIONS] COMMAND [COMMAND OPTIONS] [PATHS...]
```

## Global options

| Option | Default | Meaning |
|---|---|---|
| `--parallel N` | 8 | Maximum concurrent input files; minimum 1 |
| `-v`, `--verbose` | Off | Increase verbosity; repeat for more detail |
| `-q`, `--quiet` | Off | Suppress routine output and interactive credential prompts |
| `--plain` | Automatic | Use the non-live renderer |
| `--ansi` | Automatic | Force live rendering; `--plain` takes precedence if both are supplied |
| `--help` | | Show help |

Global options go before the command. Device, model, and engine options belong
to their individual commands.

## Input selection

Processing commands accept one or more paths, or `-i/--input-list/--file-list FILE`.
Directories are scanned recursively. CHAT commands accept `.cha` and `.chat`;
media discovery accepts `.wav`, `.mp3`, `.m4a`, `.flac`, `.ogg`, `.mp4`, `.mov`,
and `.m4v`. Actual decoding support depends on the media backend.

```bash
batchalign morphotag first.cha second.cha -o tagged/
batchalign transcribe -i recordings.txt -o transcripts/ --lang eng
```

A list is a UTF-8 text file containing one path per line. Blank lines and lines
whose first non-space character is `#` are ignored. List entries are resolved
relative to the list's directory. Positional paths are relative to the command's
working directory. Paths are deduplicated after resolving them; a repeated entry
is processed once. Whitespace around list entries is trimmed.

`-o/--out DIR` selects an output directory. Relative subdirectories are mirrored
from the common input root. Without it, CHAT transformation commands write beside
or over their input as described below. See [Command I/O](../reference/command-io.md).

## Commands

| Command | Purpose |
|---|---|
| `transcribe` | Recording to CHAT transcript |
| `align` | Forced alignment of CHAT against audio |
| `morphotag` | Add `%mor` and `%gra` |
| `utseg` | Revise utterance segmentation |
| `translate` | Add translation tiers |
| `compare` | Compare CHAT against `.gold.cha` references |
| `convert` | Convert media to WAV or MP3 |
| `diarize` | Assign speakers to existing timed CHAT |
| `ai` | Apply an AI editing instruction to CHAT |
| `cache` | Inspect or clear the result cache |
| `version` | Print version and build information |
| `daemon` | Run the separate HTTP service |

## transcribe

Accepts the shared input selection and `-o/--out` options above.

| Option or argument | Default | Details |
|---|---|---|
| `--engine` | rev | Choices: `rev`, `whisper`, `chatwhisper`, `openai`, `funaudio`, `tencent`, `qwen3`, `aliyun`, `malayalam`, `google`. ASR engine: rev \| google \| whisper \| chatwhisper \| openai \| funaudio \| tencent \| qwen3 \| malayalam. |
| `--lang` | Required | ISO-639-3 alpha_3 code: eng, cmn, yue, spa, … (Required.) |
| `--model` | Unset | ASR model id (engine-specific default if omitted). |
| `--diarize/--no-diarize` | False | Run speaker diarization with --diarize-engine after utterance segmentation. |
| `--diarize-engine` | pyannote-ai | Choices: `pyannote-ai`, `pyannote`. Diarization engine: pyannote-ai (cloud, default) or pyannote (local). |
| `--num-speakers`, `-n` | 2 | Expected speaker count (diarization hint). |
| `--force-cpu` | False | Run local inference, including utterance segmentation, on CPU (BA2's --force-cpu). |
| `--allow-mps` | False | Explicitly allow local ASR and utterance-segmentation models to use Apple MPS. Off by default because sustained MPS inference can be unstable; CHATWhisper remains float32 when selected. |
| `--wor/--nowor` | False | Include word-level timing (`%wor` and inline word bullets); omitted by default. |

## align

Accepts the shared input selection and `-o/--out` options above.

| Option or argument | Default | Details |
|---|---|---|
| `--engine` | wav2vec | Choices: `wav2vec`, `whisper_fa`, `qwen`. Forced-alignment engine: wav2vec \| whisper_fa \| qwen. |
| `--model` | Unset | FA model id (engine-specific default if omitted; wav2vec picks per the file language). |
| `--force-cpu` | False | Run the FA model on CPU (BA2's --force-cpu). Needed for whisper_fa on Apple MPS, where Whisper's bfloat16 attention kernel is unsupported. |
| `--allow-mps` | False | Explicitly allow local alignment models to use Apple MPS. Off by default because sustained MPS inference can be unstable. |
| `--utr-engine` | rev | Choices: `off`, `whisper`, `rev`. Utterance Timing Recovery backend: rev \| whisper \| off. When non-off, runs `Task.Utr` before FA to recover utterance bullets on fully-untimed CHATs. Automatically skipped when *any* utterance already carries a bullet — UTR is intended for fully-untimed transcripts only. |
| `--utr-model` | Unset | UTR model id (only used when --utr-engine=whisper; default is openai/whisper-large-v3 to match BA2's transcribe). |

## morphotag

Accepts the shared input selection and `-o/--out` options above.

| Option or argument | Default | Details |
|---|---|---|
| `--retokenize/--no-retokenize` | False |  |
| `--clear-existing/--keep-existing` | True | If true (default), drop any pre-existing %mor:/%gra: tiers from each input before tagging so re-runs regenerate. Use --keep-existing to preserve them and let the engine skip already-tagged utterances. |

## utseg

Accepts the shared input selection and `-o/--out` options above.

| Option or argument | Default | Details |
|---|---|---|
| `--stanza-fallback/--no-stanza-fallback` | False |  |
| `--language` | en |  |
| `--force-cpu` | False | Run utterance segmentation on CPU. |
| `--allow-mps` | False | Use Apple MPS for utterance segmentation when available. |

## translate

Accepts the shared input selection and `-o/--out` options above.

| Option or argument | Default | Details |
|---|---|---|
| `--target` | eng | Target language code (ISO 639-3). |
| `--engine` | google | Choices: `google`, `nllb`, `tencent`, `aliyun`.  |

## compare

Accepts the shared input selection and `-o/--out` options above.

| Option or argument | Default | Details |
|---|---|---|

## convert

Accepts the shared input selection and `-o/--out` options above.

| Option or argument | Default | Details |
|---|---|---|
| `--format` | Required | Choices: `mp3`, `wav`. Output format: mp3 or wav. |

## diarize

Accepts the shared input selection and `-o/--out` options above.

| Option or argument | Default | Details |
|---|---|---|
| `--engine` | pyannote-ai | Choices: `pyannote-ai`, `pyannote`. Diarization engine: pyannote-ai (cloud) or pyannote (local). |
| `--num-speakers`, `-n` | 0 | Expected speaker count; zero auto-detects. |

## ai

Accepts the shared input selection and `-o/--out` options above.

| Option or argument | Default | Details |
|---|---|---|
| `INSTRUCTION` | Required | Instruction applied to every utterance. |
| `--engine` | dspy | Choices: `dspy`.  |
| `--model` | zai-org/GLM-5.2 | DSPy LM model string. |
| `--max-tokens` | 1024 | Maximum output tokens for the DSPy LM call. |
| `--timeout` | 30 | Per-utterance DSPy LM timeout in seconds. |

## daemon

| Option or argument | Default | Details |
|---|---|---|
| `--host` | 127.0.0.1 | Bind address. Use 0.0.0.0 to accept off-host connections; default loopback-only so an unsecured daemon can't be exposed accidentally. |
| `--port` | 8765 | Bind port. |
| `--workers` | 1 | Worker process count. Pinned to 1 by default — the in-memory job registry is per-process. Overriding requires a shared registry backend (not yet wired). |
| `--log-level` | info | uvicorn log level: critical/error/warning/info/debug/trace. |
| `--access-log/--no-access-log` | True | Emit HTTP access logs (one line per request). |
| `--proxy-headers/--no-proxy-headers` | True | Trust X-Forwarded-* headers from the upstream reverse proxy. Combine with --forwarded-allow-ips when fronted by nginx/ALB. |
| `--forwarded-allow-ips` | 127.0.0.1 | Comma-separated upstream IPs trusted for X-Forwarded-*. Use '*' only when the daemon is behind a trusted proxy. |
| `--graceful-timeout` | 30 | Seconds to wait for in-flight requests to drain on SIGTERM. |
| `--dev` | False | Development mode: enable --reload, drop production defaults. Never use in production — disables clean shutdown handling. |

## cache

```bash
batchalign cache path
batchalign cache stats
batchalign cache clear [--yes]
```

See [Manage the result cache](cache-management.md).

## version

```bash
batchalign version
```

## Removed or unregistered interfaces

The current command registry does not expose `serve`, `jobs`, `logs`, `setup`,
`doctor`, `bench`, `benchmark`, `eval`, or `coref`. A coreference recipe and backend interface
exist in the Python API, but the module under `cli/hidden/` is not registered as
a public command. Old server and benchmark examples are not current CLI syntax.
