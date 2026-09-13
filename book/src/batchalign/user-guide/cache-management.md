# Manage the result cache

Use these commands when you need to inspect stored results or force a fresh run.
They operate on the default result cache, not downloaded models.

## Inspect the cache

```bash
batchalign cache path
batchalign cache stats
```

`path` prints the directory. `stats` prints its apparent file size and latest
modification time, or reports that the cache is absent. It does not count entries.

## Clear saved results

Finish or stop processing jobs that use the cache, then run:

```bash
batchalign cache clear
```

Confirm the displayed path when prompted. For an unattended script:

```bash
batchalign cache clear --yes
```

The next processing run recomputes the required backend results and can save them
again. Your transcripts, recordings, and downloaded models remain in their own
locations.

The current CLI has no per-run cache bypass flag. Python callers can use
[`CacheSpec.bypass()` or `CacheSpec.refresh()`](python-api.md#cache-policy).
