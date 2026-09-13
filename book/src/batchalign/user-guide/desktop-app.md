# Run the desktop application from source

The Batchalign desktop application lives in `apps/batchalign/batchalign-gui/`.
It uses React and Tauri, with a bundled Python HTTP-service sidecar.

From a development checkout with the repository build tools installed:

```bash
just batchalign gui dev
```

The Bazel dependency graph builds and stages the sidecar. To create a desktop
bundle, use `just batchalign gui build`.

In the application, choose an input folder, add a pipeline step, review the
step's language and engine settings, choose the output location, and start the
batch. Inspect the completion status and generated files. The exact available
recipes and backends come from the service's capabilities.

For ordinary command-line use, start with the [Quick Start](quick-start.md).
The CLI does not require the desktop service to be running.
