# The HTTP service and the CLI

Ordinary `batchalign morphotag`, `align`, and `transcribe` commands create and run
a pipeline in their own process. They do not start or discover an HTTP daemon,
and they do not accept a global `--server` option.

The desktop application uses a separate **Python FastAPI service**, packaged
as a PyApp sidecar. That service exposes recipes and job progress to the GUI.
It can also be started explicitly with `batchalign daemon` for API development
or integration. This is distinct from CLI file concurrency.

The service keeps its job registry in memory. It does not provide the retired
Rust server's worker registry, `server.yaml` fleet configuration, Temporal job
persistence, or automatic CLI routing. Do not rely on jobs surviving a service
restart.

For instructions, see [Run the HTTP service](server-setup.md). For local CLI
throughput, see [Tune file concurrency](worker-tuning.md).
