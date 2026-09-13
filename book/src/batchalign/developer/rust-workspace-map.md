# Batchalign source map

| Location | Responsibility |
|---|---|
| `crates/batchalign/batchalign-core/` | Typed tasks, task runners, CHAT processing, ASR cleanup, protocol schemas |
| `crates/batchalign/batchalign-engine/` | PyO3 runtime, pipelines, backend routing, batching, LMDB, outcomes |
| `python/batchalign/cli/` | Typer CLI, input selection, terminal UI, output handling |
| `python/batchalign/backends/` | Model and service adapters, including Stanza token processing and rendering |
| `python/batchalign/recipes.py` | Standard task compositions |
| `python/batchalign/api.py` | FastAPI recipe endpoints and in-memory job lifecycle |
| `apps/batchalign/batchalign-gui/` | React/Tauri desktop application |
| `bazel/python/` | Wheel, PyApp, and protocol build integration |
| `just/batchalign.just` | Product build, test, and CLI recipes |

The Python package imports the extension as `batchalign._core`. Typed protocol
schemas come from the Rust core; Bazel generates the Python wire types.
TalkBank parser, model, and transform crates supply the CHAT representation
used by the core. Check workspace `Cargo.toml` for their exact dependency sources.

For execution flow, see [How a processing command runs](../architecture/command-lifecycles.md).
