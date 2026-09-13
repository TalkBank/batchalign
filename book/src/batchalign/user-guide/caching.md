# How result caching works

Batchalign saves backend results so repeated processing can reuse completed
computations. This includes text analysis: morphosyntax, utterance segmentation,
and translation use the same result cache as audio inference.

## Results and models are separate

The result cache stores individual task outputs in an **LMDB database**. Model
files downloaded by Stanza, Hugging Face, or other libraries live in those
libraries' own download locations. Clearing result entries does not remove model
files. Loaded models also occupy memory for the lifetime of their Python objects;
a result-cache hit and a model already loaded in memory are different kinds of reuse.

The engine checks for a cached result before sending a request to a backend.
A hit avoids that inference request. Input discovery, CHAT parsing, preprocessing,
output assembly, and file writing still happen. Some backends initialize before
cache lookup, so even a fully cached run can have startup costs.

## What is reused

| Pipeline work | Default behavior |
|---|---|
| Morphosyntax (`morphotag`) | Cache backend results per utterance |
| Utterance segmentation (`utseg`) | Cache backend results |
| Translation (`translate`) and AI editing (`ai`) | Cache backend results |
| ASR (`transcribe`), timing recovery, forced alignment (`align`) | Cache backend results |
| Speaker inference (`diarize` or transcription with diarization) | Cache backend results |
| Media conversion (`convert`) | The default conversion recipe bypasses the result cache |
| CHAT parsing, tier assembly, output writing | Performed by the pipeline; not saved as finished output files in this cache |

The cache is shared across pipeline instances and processes at the same path.
LMDB allows concurrent readers and serializes write transactions.

## When a result stops matching

A cache key combines the compiled build identity, task, backend name, and the
input fields selected by that task's `CacheKey` implementation. For example,
morphosyntax includes text, tokens, language, and retokenization mode. Routing
identifiers such as source file ID and utterance number do not participate, so
identical content in different files can share an entry.

Changing a key component causes a miss. The build identity normally comes from
the compiled Git SHA, with the Rust package version as a fallback. A package
upgrade can therefore leave older entries on disk while no longer reading them.

This does **not** fingerprint arbitrary downloaded model files or every remote
provider update. If a provider or model changes without changing the backend
identity or input, use a refresh policy in the Python API or clear the result
cache before processing again.

## Storage and limits

Run `batchalign cache path` to see the location for your installation. Defaults:

| Platform | Result-cache directory |
|---|---|
| macOS | `~/Library/Caches/batchalign/cache.lmdb/` |
| Linux | `$XDG_CACHE_HOME/batchalign/cache.lmdb/`, or `~/.cache/batchalign/cache.lmdb/` |
| Windows | `%LOCALAPPDATA%\batchalign\cache.lmdb\` |

The directory contains `data.mdb` and `lock.mdb`. The current engine sets a
16 GiB maximum LMDB map size. This is a virtual address-space limit, **not** a
16 GiB resident-memory allocation or an automatic eviction policy. Cache writes
are best effort; a full database can prevent new results from being saved.

For commands to inspect or clear entries, see [Manage the result cache](cache-management.md).
For custom paths and read/write policies, see [Python API](python-api.md#cache-policy).

Implementation: `crates/batchalign/batchalign-engine/src/cache.rs`,
`batcher.rs`, the core `proto/` input types, and `python/batchalign/recipes.py`.
