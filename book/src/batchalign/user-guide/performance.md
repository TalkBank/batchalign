# Understanding processing speed and memory use

Processing time depends on the input, backend, hardware, and cache state.
A first run may download models; a later CLI invocation still has to start
Python and initialize the backends it needs. Saved results can avoid inference,
including for text tasks such as morphosyntax. See [Caching](caching.md).

## How work overlaps

The CLI runs a Rust pipeline inside the Python process. It admits a limited
number of input files and sends their task requests to shared backend queues.
`--parallel N` controls file admission; the default is 8.

Each registered backend has one batcher. It checks the result cache, collects
misses up to the backend's batch size or batching deadline, then calls that
backend. That batcher awaits the call before starting another call. Different
backends can overlap work; `--parallel` does not create N model processes.

For morphosyntax, the current defaults are:

| Control | Value | Meaning |
|---|---:|---|
| Active files | 8 | CLI `--parallel` default |
| Pending utterances per active file | 128 | Rust morphotag dispatch window |
| Requests per Stanza backend batch | Up to 128 | Backend batch maximum |
| Batch collection window | Up to 100 ms after the first miss | Allows requests to accumulate |
| Resident Stanza pipeline configurations in the process-wide LRU | 2 | Keyed by language set and retokenization mode |

Stanza groups a received batch by language configuration. A mixed-language batch
may produce several smaller model calls. The CLI orders morphotag files by
language header, then by descending file size within a group, to improve locality.
One sufficiently large file can fill a batch without additional file concurrency.
A multilingual pipeline configuration can contain models for several languages;
the two-entry LRU is not a limit of two individual model objects.

## What the bounds do—and do not—mean

The engine bounds active file work and backend queue lengths, and morphotag
bounds pending utterance futures. These limits prevent the scheduler from
submitting the entire corpus for inference at once. They are not an RSS budget.
The CLI still discovers input paths up front, and active files retain transcript
state. Long utterances, decoded audio, model weights, inference tensors, and
allocator retention can dominate memory.

Increasing file concurrency can improve overlap or batch filling, but can also
increase RSS without speeding up inference. Increasing utterance batch size
makes each model call larger. These are separate tuning decisions.

## Device selection

Device behavior belongs to the selected backend. `align`, `transcribe`, and
`utseg` expose `--force-cpu` and an explicit `--allow-mps` option for applicable
local models. `morphotag` does not expose those flags; its Stanza configuration
uses the library's device selection. There is no universal GPU speedup factor.

## Measure your workload

Compare the same inputs, outputs, backend settings, package version, and cache
policy. Record model-download time separately from ordinary startup, and report
whether results were cached. Use utterances per second as well as files per
second when transcript lengths vary. Measure peak RSS alongside elapsed time;
a larger batch can trade substantial memory for a small throughput improvement.

For a practical file-concurrency comparison, see [Tune file concurrency](worker-tuning.md).
The current CLI has no `bench` command. The GUI's HTTP service is a separate
entrypoint; ordinary CLI processing does not automatically connect to it or keep
a background model service alive between invocations.
