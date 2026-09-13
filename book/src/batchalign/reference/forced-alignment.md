# Forced-alignment pipeline

The alignment recipe composes optional utterance timing recovery (`Utr`) and
forced alignment (`Fa`). The CLI supplies both backends by default, choosing
`wav2vec` for FA and `rev` for recovery. Setting `--utr-engine none` omits recovery.

Timing recovery uses an ASR-capable backend to establish missing utterance timing.
The UTR runner can skip work when the input is already timed. FA uses transcript
content and prepared audio to request word alignments and applies timing to CHAT.
Results travel through the same bounded backend queues and LMDB cache as other
tasks. It does not rely on a remote worker process or a separate SQLite audio cache.

## Ownership

| Concern | Source |
|---|---|
| Engine/model options and language inference | `python/batchalign/cli/align.py` |
| Task order | `python/batchalign/recipes.py::align` |
| Timing recovery and overlap strategies | `crates/batchalign/batchalign-core/src/taskrunners/utr/` |
| FA preparation and result application | Core `taskrunners/fa.rs` |
| Typed backend requests/results | Core `proto/utr.rs`, `proto/fa.rs` |
| Local model implementations | `python/batchalign/backends/fa/` and ASR backends supporting UTR |

`@Options: NoAlign` causes the FA runner to skip alignment. For an operational
walkthrough, see [Align a transcript](../user-guide/commands/align.md). For
scheduling and RSS, see [Performance](../user-guide/performance.md).
