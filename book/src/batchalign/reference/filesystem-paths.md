# Filesystem locations

| Data | Location or resolution |
|---|---|
| Provider configuration | `~/.batchalign.ini` (`python/batchalign/config.py`) |
| Default result cache | OS cache directory plus `batchalign/cache.lmdb/`; print with `batchalign cache path` |
| Input-list entries | Relative to the list file's directory unless absolute |
| Positional input paths | Relative to the invocation directory unless absolute |
| CLI output | `-o/--out`, or command-specific output beside the input |
| Downloaded models | The selected model library's own cache/resource directory |

There is no single Batchalign directory that owns all downloaded models. Stanza,
Hugging Face, and other backends use their own loaders. The old
`BATCHALIGN_ANALYSIS_CACHE_DIR`, `BATCHALIGN_MEDIA_CACHE_DIR`, and Rust
`server.yaml` examples do not configure the current result cache.

Python callers select a result-cache path with `CacheSpec(path=...)`.
See [Caching](../user-guide/caching.md) and [Command I/O](command-io.md).
