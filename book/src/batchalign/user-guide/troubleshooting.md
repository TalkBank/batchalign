# Troubleshoot a processing run

## The command cannot be found

Close and reopen Terminal or PowerShell after installation, then try
`batchalign --help`. If it is still unavailable, repeat the
[installation steps](installation.md) and check that the installer finished.

## An option or command is unknown

Run `batchalign --help` and `batchalign COMMAND --help` using your installed
version. The current global concurrency flag is `--parallel`; engine selection
uses command-specific `--engine` options. The CLI does not expose the older
`serve`, `setup`, `logs`, `doctor`, or `bench` interfaces.

## A processing command appears to be waiting

The first use of a backend can download models. An interactive cloud backend may
also be waiting for credentials. Keep the command window open and read its latest
message. Use `batchalign -v COMMAND ...` for more detail or `--plain` before the
command to avoid live terminal rendering. See [Model downloads](model-downloads.md).

## The transcript cannot be parsed

Read the error's file location and CHAT diagnostic. Fix the indicated transcript
and rerun a single file before processing the folder again. For morphology, check
`@Languages:` and the CHAT header structure. Use the
[CHAT format reference](../../chat-format/overview.md) to interpret markup.

## Alignment cannot find the recording

Check the transcript's `@Media:` header, keep the referenced recording beside the
CHAT file, and confirm that the recording is readable. Use a small single-file
run to check the pairing. The current local CLI does not use the old server's
remote media mappings.

## The computer runs out of memory

Lower file concurrency, for example:

```bash
batchalign --parallel 1 morphotag corpus/ -o tagged/
```

For commands that expose it, `--force-cpu` selects CPU inference; it is not a
morphotag option. Long transcripts and model batch sizes still affect memory at
`--parallel 1`. See [Performance](performance.md).

## A repeat run gives the same unexpected result

Check and correct the input first. If you need to rule out saved backend results,
finish active processing and [clear the result cache](cache-management.md), then
rerun. Removing model files is a separate operation and is not required to clear
saved results.

## Report a reproducible problem

Include the output of `batchalign version`, your operating system, the exact
command with credentials removed, and the final error text. Attach a small input
that reproduces the problem if you can share it. Say whether it also happens with
a fresh result cache. Report issues in the Batchalign repository.
