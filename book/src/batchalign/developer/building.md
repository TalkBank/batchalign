# Build Batchalign from source

Use the repository's `just` recipes from the checkout root. They invoke Bazel
and materialize the Rust extension, Python dependencies, and generated protocol
types required by each target.

```bash
just batchalign build debug
just batchalign test debug
just batchalign cli --help
```

`just batchalign cli` is the authoritative development CLI entrypoint. It restores
the invocation directory before running the Bazel Python binary, so relative
input paths behave as they do in an installed CLI.

## Build release artifacts

```bash
just batchalign wheel
just batchalign sidecar
just batchalign gui build
```

`wheel` produces the host-platform Python wheel in `python/target/wheels/`.
`sidecar` builds the PyApp-bundled HTTP service. The GUI bundle embeds that sidecar.
Cross-platform wheel builds run in the GitHub Actions matrix.

## Run checks

```bash
just batchalign test
just batchalign pytest
just batchalign lint
just batchalign gui test
just docs build
```

See [Testing](testing.md) for scope. `just batchalign versions` shows the version
sources; `just --list batchalign` lists recipes. Use the repository wrappers
instead of a separate editable-install procedure for ordinary development.
