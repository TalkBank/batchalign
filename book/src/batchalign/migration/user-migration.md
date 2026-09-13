# Update commands and integrations

1. Update the `batchalign` package using the [installer](../user-guide/installation.md).
   Check `batchalign version` before comparing behavior.
2. Replace the former global `--workers N` flag with `--parallel N`. It controls
   active files, not model-process replicas.
3. Use command-specific `--engine` options for ASR and FA. Check the actual choices
   with `batchalign COMMAND --help`; old engine names are not all interchangeable.
4. Use `-o/--out` for a destination. Processing commands accept multiple paths
   and `-i/--input-list/--file-list`.
5. Remove old automatic-server, fleet, benchmark, and cache-override flags.
   Ordinary CLI processing now runs in process. The separate `daemon` is an HTTP
   service for GUI/API integrations.
6. Update cache assumptions: text and audio backend results use LMDB. See
   [Caching](../user-guide/caching.md) before comparing repeat-run performance.
7. For Python integrations, use the current `Pipeline`, recipe, input, and backend
   interfaces. The old BA2 document/pipeline classes are not drop-in equivalents.

Run a small copied input through the revised workflow before processing a corpus.
The [CLI reference](../user-guide/cli-reference.md) lists the supported surface.
