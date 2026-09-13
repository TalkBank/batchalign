# Tune file concurrency

Use `--parallel` when you want to change how many files a processing command can
work on at once. Start with the default, 8. If memory use is too high, reduce it:

```bash
batchalign --parallel 2 morphotag corpus/ -o tagged/
```

The option goes **before** the command name. Its minimum is 1. Scripts using the
old global `--workers` option should use `--parallel` instead.

## Compare settings

1. Choose a representative set of files, including the longer transcripts or
   recordings you normally process.
2. Run with `--parallel 1` and a separate output folder. Record elapsed time and
   peak resident memory with your operating system's monitoring tools.
3. Repeat with `--parallel 4`, then 8 if memory permits. Keep the inputs and
   backend options unchanged.
4. Compare runs with the same cache state. A cached second run is not evidence
   that a higher concurrency setting improved inference. To compare uncached
   CLI runs, [clear the result cache](cache-management.md) between trials after
   each job finishes.
5. Keep the smallest setting that gives useful throughput on your workload.

For morphotag, active files share one Stanza batcher. Increasing `--parallel`
does not create additional Stanza replicas. The default utterance dispatch
window and backend batch maximum are both 128; there is no CLI batch-size flag.
Python callers can set `StanzaBackend(batch_size=..., batch_window_ms=...)`, but
that does not change the Rust per-file dispatch window.

The Python `Pipeline` and recipe APIs still name file concurrency `workers`.
For the scheduling and memory model, see [Performance](performance.md).
