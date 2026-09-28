# Batch Processing

**Status:** Current
**Last updated:** 2026-03-30 13:40 EDT

This chapter covers workflows that operate on multiple files at once -- directory-level analysis, corpus-scale validation, and integration with the `chatter` CLI and batchalign for bulk operations.

## Directory-Level CLAN Analysis

The extension supports running any of the 33 CLAN analysis commands on an entire directory of `.cha` files.

### From the Explorer

1. Right-click on a folder in the VS Code Explorer sidebar
2. Select **Run CLAN Analysis on Directory**
3. A QuickPick lists all 33 available commands (freq, mlu, mlt, etc.)
4. Select a command
5. The extension runs the analysis across all `.cha` files in the directory
6. Results are aggregated and displayed in a single Analysis Panel

The LSP's `resolve_files()` function walks the directory tree to find all `.cha` files. Results display as styled tables with section headings, key-value statistics, and bar charts -- the same rendering used for single-file analysis.

> **(SCREENSHOT: Analysis Panel showing aggregated results from a directory-level FREQ analysis)**
> *Capture this: Right-click a folder containing several .cha files, run FREQ analysis, show the results panel with aggregated frequency tables*

### CSV Export

Both single-file and directory-level analysis results can be exported to CSV:

1. Click the **Export CSV** button in the Analysis Panel toolbar
2. Choose a save location in the file dialog
3. The CSV file contains all visible tables and statistics

This is useful for importing results into spreadsheets or statistical software (R, SPSS, etc.).

## Corpus-Scale Validation

The [Validation Explorer](corpus-validation.md) provides a tree view for validating entire directory trees. For even larger-scale validation, the `chatter` CLI can be used directly from the terminal:

```bash
# Validate an entire corpus directory
chatter validate path/to/corpus/ --force

# Validate with roundtrip checking (parse then re-serialize, compare)
chatter validate path/to/corpus/ --roundtrip --force

# Faster validation (skip tier alignment checks)
chatter validate path/to/corpus/ --skip-alignment

# JSON output for programmatic consumption
chatter validate path/to/corpus/ --format json

# Limit error output
chatter validate path/to/corpus/ --max-errors 100

# Control parallelism
chatter validate path/to/corpus/ --jobs 4
```

The CLI runs validation in parallel using crossbeam workers. Results are cached in SQLite for instant re-display on subsequent runs.

## Integration with batchalign

A common workflow for processing a corpus involves multiple stages:

### Align, Morphotag, Validate Cycle

```bash
# 1. Automatic transcription and alignment
batchalign transcribe audio_corpus/ -o transcribed/ --lang eng

# 2. Add morphological annotation (no --lang — language read per-file from @Languages)
batchalign morphotag transcribed/ -o annotated/

# 3. Validate the results
chatter validate annotated/ --force

# 4. Open in VS Code for review and correction
code annotated/
```

### Bulk Alignment Repair

```bash
# Repair timing bullets on an existing corpus
batchalign align --bullet-repair corpus/ -o repaired/

# Validate the repaired files
chatter validate repaired/ --force

# Open for post-alignment review
code repaired/
```

After opening the repaired corpus in VS Code, use [Review Mode](post-alignment-review.md) to step through and verify the alignment.

## Using chatter CLI for Bulk Operations

The `chatter` CLI supports several bulk operations that complement the VS Code extension:

| Command | Purpose |
|---------|---------|
| `chatter validate` | Validate files or directories |
| `chatter normalize` | Reformat CHAT files to canonical form |
| `chatter to-json` | Convert CHAT to JSON for programmatic processing |
| `chatter clan freq` | Run frequency analysis |
| `chatter clan mlu` | Compute mean length of utterance |

All CLI commands accept directories and process files in parallel. Use `--help` on any command for full usage.

## Tips for Batch Workflows

- **Use `--force` for fresh results.** The cache speeds up repeated runs, but use `--force` when you have modified files and want guaranteed fresh validation.

- **Start with validation.** Before running analysis commands, validate the corpus first. Analysis on malformed CHAT files can produce misleading results.

- **Monitor memory on large corpora.** The CLI processes files in parallel. For very large corpora (tens of thousands of files), use `--jobs N` to limit parallelism if memory is a concern.

- **Use JSON output for automation.** `chatter validate --format json` produces machine-readable output that can be piped to other tools for automated quality checks in CI pipelines.

## Related Chapters

- [Corpus Validation](corpus-validation.md) -- the Validation Explorer tree view
- [Post-Alignment Review](post-alignment-review.md) -- reviewing batchalign output in VS Code
- [Cache Management](../configuration/cache.md) -- cache location and clearing
