# Run the HTTP service

Use this guide for API development or a GUI integration. You do not need an
HTTP service to process files with the CLI.

1. Install the `api` extra in your Batchalign environment. The standard bootstrap
   installation includes the `all` extra, which includes API dependencies.
2. Start the service in your command window:

   ```bash
   batchalign daemon --host 127.0.0.1 --port 8765
   ```

3. Open `http://127.0.0.1:8765/docs` for the API schema, or request
   `http://127.0.0.1:8765/capabilities` to discover recipes and backends.
4. Stop the foreground service with Ctrl-C when finished.

Keep the default one Uvicorn worker: the job registry is process-local. The
`daemon --workers` option concerns HTTP processes; it is unrelated to the CLI's
global `--parallel` option. For supervised operation, run the foreground command
under your service manager.

For local path-based API inputs, the service requires
`BATCHALIGN_API_ALLOW_PATHS=1`. Enable it only for a trusted local integration:
those paths are interpreted on the machine running the service. The desktop
sidecar sets up its own local connection.

The service has no `serve start`/`serve stop` command group or `server.yaml`
configuration. See [CLI reference](cli-reference.md#daemon) for supported options.
