# Add an inference backend

1. Choose the task interface in `python/batchalign/backends/base.py`. Implement
   the corresponding backend marker, a stable `name`, its `BatchPolicy`, and
   `call` behavior. Start from an existing backend for the same task.
2. Return the typed output expected by the core `proto/` definition. Preserve
   input/output correspondence and return one output per input in a batch.
3. Include output-affecting model/configuration changes in backend identity when
   they are not already in the typed input. The engine uses that name in cache keys.
4. Export the backend through the package's lazy import surface where appropriate,
   add its dependencies to the relevant `python/pyproject.toml` extra, and supply
   it to a recipe. For a CLI engine choice, update that command's enum and builder.
5. Test protocol shape and failure behavior with deterministic fixtures, then
   perform a small real-backend smoke run through `just batchalign cli`.
6. Update the command reference and any backend-specific instructions.

Batching and result caching are engine responsibilities. Do not add a worker
process or a second cache solely to integrate an ordinary Python backend.
A genuinely new task also needs core input/output types, a runner, and routing
registration; inspect the existing task family before extending those contracts.

See [Source map](rust-workspace-map.md), [Python API](../user-guide/python-api.md),
and [Testing](testing.md).
