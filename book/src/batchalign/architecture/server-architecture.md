# How the HTTP service runs pipelines

The desktop GUI uses the FastAPI application in `python/batchalign/api.py`.
Recipe discovery exposes available task compositions and backend descriptors;
requests materialize typed inputs and create a pipeline through the recipe API.
Job status, events, results, and cancellation are exposed through `/jobs/{job_id}`
and its associated routes.

The default job registry is in memory. A service restart loses registry state,
and separate Uvicorn processes do not share it. This is why the daemon defaults
to one HTTP worker. The service is packaged with Python and the wheel in a PyApp
sidecar for the Tauri application.

The desktop starts the sidecar on a loopback port and discovers the bound port
from its `DAEMON_PORT` announcement. The ordinary CLI invokes pipelines directly
and does not use this handshake or service lifecycle.

Backend batching and caching follow the same engine contracts as the
[local pipeline](command-lifecycles.md). The API's job registry is not the LMDB
result cache, and persistent result entries do not make jobs restartable.

For API integration, inspect the running service's `/docs` and `/capabilities`.
See [Run the HTTP service](../user-guide/server-setup.md) for startup instructions.
