# Read processing progress

The CLI tracks each selected file through task stages and prints a final summary
of completed, failed, and skipped work. Multiple active files can be at different
stages. The terminal renderer is selected automatically; use global `--plain`
for line-oriented output or `--ansi` to request live rendering.

```bash
batchalign --plain morphotag corpus/ -o tagged/
batchalign -v align corpus/ -o aligned/
```

Rust progress events reach Python callbacks and the terminal task model. Backend
calls may report finer progress, but a batched call cannot always attribute a
sub-step to each file. A quiet progress counter alone does not establish that
inference is stuck. Startup can also include downloads and model initialization.

File completion and output writing happen as outcomes arrive on the CLI's
callback path. Text commands do not submit the entire corpus as one model call.
See [Performance](performance.md) for scheduling and [Troubleshooting](troubleshooting.md)
if a run is not advancing.
