# Python API reference

The `batchalign` Python package exposes a Rust-backed `Pipeline`, task and input
types, backend classes, and recipe functions. The CLI uses this API too.

## Run a recipe

```python
import batchalign as ba
from batchalign.inputs import chat_from_path

pipeline = ba.recipes.morphotag(
    stanza_backend=ba.StanzaBackend(),
    workers=4,
)
results = pipeline.run([chat_from_path("sample.cha")])
```

`workers` limits concurrent files. A recipe supplies a task sequence and backend
instances to `Pipeline`; backend constructors hold model-specific settings.
`pipeline.run()` returns outcomes. It does not perform the CLI's output-file
writing step. See the outcome type and serialization methods in
`crates/batchalign/batchalign-engine/src/py_outcome.rs` when integrating output.

## Cache policy

Recipes forward pipeline options such as `cache`:

```python
pipeline = ba.recipes.morphotag(
    stanza_backend=ba.StanzaBackend(),
    cache=ba.CacheSpec.bypass(),
    workers=1,
)
```

| Policy | Reads saved results | Writes new results |
|---|---|---|
| `ba.CachePolicy.Use` (default) | Yes | Yes |
| `ba.CachePolicy.Bypass` / `ba.CacheSpec.bypass()` | No | No |
| `ba.CachePolicy.Refresh` / `ba.CacheSpec.refresh()` | No | Yes |

To use a separate database:

```python
cache = ba.CacheSpec(path="/path/to/cache.lmdb", policy=ba.CachePolicy.Use)
```

The CLI's cache-management commands target the default path returned by
`ba.default_cache_path()`. They do not discover custom API cache paths.

## API source

- `python/batchalign/__init__.py`: exported types and lazy imports.
- `python/batchalign/recipes.py`: standard task compositions.
- `python/batchalign/inputs.py`: file-based input constructors.
- `python/batchalign/backends/`: backend constructors and interfaces.
- `crates/batchalign/batchalign-engine/src/pipeline.rs`: pipeline constructor and execution.

The old BA2 `BatchalignPipeline` and document model are not interchangeable with
this API. Use the current types when migrating integrations.
