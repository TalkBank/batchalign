# Performance

**Status:** Current
**Last updated:** 2026-05-01 22:47 EDT

This page covers what to expect from Batchalign's processing times and how to
improve throughput.

## Cold vs warm starts

The first run of any command downloads ML models and initializes them — expect
5-20x longer than subsequent runs. After the first run:

- **Model cache:** Stanza, Whisper, and other ML models are cached on disk
  (~2 GB total). They load from cache on subsequent runs.
- **Server warmth:** When an explicit server is running, workers can stay warm
  in memory across multiple jobs. Direct local execution does not keep a daemon
  alive between CLI invocations.
- **Analysis cache:** Batchalign caches **audio-bound** intermediate
  results (forced-alignment word timings, UTR ASR) in a local SQLite
  database keyed by content hash. Re-running `align` or `transcribe` on
  the same audio reuses these and is much faster. Text-NLP commands
  (`morphotag`, `utseg`, `translate`, `coref`) are **not cached** — see
  [Caching](caching.md).

| Scenario | Relative Speed |
|----------|---------------|
| First run (model download + init) | 1x (baseline) |
| Cold start (models cached on disk) | 3-5x faster |
| Warm server (models in memory) | 5-20x faster |
| Cached audio task (`align` / `transcribe` UTR re-run) | Near-instant |

## File concurrency

`--parallel N` controls the maximum number of active input files (default: 8).
Place it before the command:

```bash
batchalign3 --parallel 4 morphotag ~/corpus/ -o ~/output/
```

Active files share the backend batcher. Morphotag uses one Stanza call at a
time, with up to 128 utterances per batch. Increasing file concurrency can
improve batch filling without creating additional model replicas.

## CPU vs GPU

Batchalign automatically uses GPU acceleration when available (CUDA on Linux,
MPS on macOS). To force CPU-only processing:

```bash
batchalign3 morphotag ~/corpus/ -o ~/output/ --force-cpu
```

CPU-only is slower but uses less memory and avoids GPU driver issues. On
machines without a supported GPU, CPU mode is selected automatically.

## Memory patterns

Memory depends on the loaded models, active files, and inference batch size.
`--parallel N` bounds the number of active files, so larger values can retain
more parsed transcripts and pending inputs. It does not multiply the number
of Stanza model instances by N.

Batch length also matters: 128 long utterances can require substantially more
memory than 128 short ones. File concurrency and backend batch size should be
tuned separately.

Audio is loaded on demand; concurrent files can also retain decoded audio.

## Server mode for warm models

For repeated interactive use, keep models loaded in the background:

```bash
batchalign3 serve start
```

Subsequent commands automatically connect to the running daemon. Stop it when
done:

```bash
batchalign3 serve stop
```

See [Server Mode](server-mode.md) for configuration details and
[Worker Tuning](worker-tuning.md) for memory budgets and warmup configuration.

## The `bench` command

Measure processing throughput on your hardware. The shape is
`bench <command> <in_dir> <out_dir>` — both directories are required
positional arguments:

```bash
batchalign3 --parallel 1 bench morphotag ~/sample-corpus/ ~/bench-out/
batchalign3 --parallel 4 bench morphotag ~/sample-corpus/ ~/bench-out/
```

This runs the command with timing instrumentation and reports files/second and
wall-clock time per file. Use `--runs N` to repeat the run, `--use-cache` to
keep cache lookups enabled (the default is to bypass cache for clean
benchmarks), and `--dataset <label>` to tag structured output.

## Estimated times per command

Rough estimates for a single file (~100 utterances) on a modern laptop with
warm daemon:

| Command | Warm Daemon | Cold Start |
|---------|------------|------------|
| `morphotag` | 2-5 seconds | 30-60 seconds |
| `align` | 5-15 seconds | 45-90 seconds |
| `transcribe` | 10-60 seconds (depends on audio length) | 60-120 seconds |
| `translate` | 2-5 seconds | 30-60 seconds |
| `utseg` | 3-8 seconds | 30-60 seconds |
| `compare` | <1 second | <1 second |

Times vary significantly with hardware, file size, and language. GPU
acceleration typically provides a 2-5x speedup for model inference.
