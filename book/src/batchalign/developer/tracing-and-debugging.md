# Diagnose a pipeline failure

1. Reproduce with one small input through `just batchalign cli`, using a separate
   output directory. Preserve the original failing input.
2. Add global `-v` or `-vv` and capture the command's error text. Use `--plain`
   when saving terminal output to a file.
3. Determine whether failure occurs during input parsing, backend construction,
   backend inference, result application, or output writing. Use the
   [source map](rust-workspace-map.md) to find the owning layer.
4. Compare cached and fresh behavior when relevant using the Python cache policy
   or the CLI cache-management command after active processing stops.
5. Add a focused regression case at the layer that owns the defect. A fake
   backend can isolate scheduler and result-injection behavior from model behavior.

The current CLI does not expose the retired `--debug-dir`, server job logs, or
worker-protocol trace commands. Inspect `Outcome.error`, progress callbacks, and
the Python/Rust logging surfaces used by the current pipeline. Include version,
command, input shape, and cache state in a reproducible report.
