# Compare a transcript with a reference

Use `compare` when you have a transcript and a checked reference transcript.

1. Place `session.cha` and `session.gold.cha` in the same folder. Alternatively,
   use `template.gold.cha` as the reference for files in that folder; a per-file
   `.gold.cha` takes precedence.
2. Run:

   ```bash
   batchalign compare corpus/ -o comparisons/
   ```

3. Inspect the generated comparison metrics and the command's summary. Gold
   files are references, not separate inputs to score. Files without a matching
   reference are skipped by input pairing.

See [CLI reference](../cli-reference.md#compare) for input selection.
