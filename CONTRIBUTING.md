# Contributing to Batchalign

**Last updated:** 2026-08-30 12:03 EDT

Batchalign combines a typed Rust pipeline, Python model backends, and a desktop
shell. CHAT infrastructure is consumed from the pinned TalkBank Chatter
dependency.

## Setup and commands

Install the toolchains pinned by the repository, then use the Bazel-backed
recipes from the workspace root:

```bash
just batchalign build debug
just batchalign test debug
just batchalign pytest
just batchalign lint
just batchalign cli -- --help
```

The CLI recipe is the supported development entrypoint. It rebuilds the
`//python/batchalign` `py_binary` and restores the caller's working directory so
relative input paths behave normally.

Local Bazel work uses one job by default. Increase `BATCHALIGN_BAZEL_JOBS` only
on a host with enough memory. Do not run Rust/Bazel compilation concurrently
with Stanza, Whisper, or other model-bearing fixture runs.

### Windows build prerequisites

Install Git for Windows (including Bash), Visual Studio 2022 Build Tools with
the Desktop development with C++ workload and Windows SDK, Node.js 22, Rustup,
Just, and Bazelisk. Make `bash`, `node`, `cargo`, `just`, and `bazel` available
on PATH. The repository selects its Rust and Bazel versions automatically.

Enable Windows Developer Mode before building. The Bazel Rust dependency
resolver creates symbolic links while assembling its Cargo workspace; without
Developer Mode or the corresponding Windows privilege, it fails with
`A required privilege is not held by the client (os error 1314)` before compiling
the sidecar.

Enable Git's long-path support with `git config --global core.longpaths true`.
The pinned Chatter dependency includes nested snapshot filenames that exceed
Windows' default path limit under Bazel's dependency cache. After changing
either prerequisite, run `just batchalign shutdown` to discard cached resolver
failures before retrying the build.

Use a short Bazel cache path without spaces. In the gitignored `.bazelrc.user`,
add `startup --output_user_root=C:/b` (or another writable short directory).
The Windows Rust bootstrap wrapper substitutes the cache path into compiler
arguments without quoting it; a user profile containing spaces otherwise causes
`--remap-path-prefix must contain '=' between FROM and TO` during compilation.

Build the Windows desktop bundle from the repository root with
`just batchalign gui build release --target x86_64-pc-windows-msvc`.

For installed-app acceptance, install the NSIS bundle for the current user
(the MSI's default all-users install requires elevation). Put `tauri-driver`
2.0.6 and the `msedgedriver` matching the installed WebView2 runtime on PATH.
Run `scripts/packaged-sidecar-smoke.mjs` from the GUI directory against the
installed `sidecar.exe` to produce a packaged runtime report, then run
`scripts/native-webview-smoke.mjs <installed-Batchalign.exe> <packaged-report.json>`.
The native test uses the app's default runtime location and requires that
location to be absent for a cold run; it does not delete an existing runtime.

On Windows the native test removes host Python/build tools from the child
PATH, starts with empty model caches, and temporarily moves the actual pip
and PyApp caches aside, restoring them in `finally`. Run it exclusively:
other pip installs or PyApp bootstraps must not run concurrently. Its report
records the isolated paths, visible startup progress, launches, native folder
selection, comparison output, and process cleanup. `BATCHALIGN_SMOKE_MODELS=1`
also exercises morphology through the UI and the real inference fixtures.
For a subsequent model run, `--warm` explicitly reuses the installed runtime;
set `BATCHALIGN_NATIVE_EVIDENCE` to a different evidence directory to retain
the cold-run report. Warm runs are not clean-bootstrap evidence.
Set `BATCHALIGN_NATIVE_CHAT` to a validated CHAT file to use it for the Windows
UI morphology check; the report records its path and hash. The harness works
on copies. Comparison retains its known exact-match fixture.
To run native acceptance directly without a preceding sidecar test, its second
argument may be a JSON path descriptor with `binary` pointing to the installed
sidecar and `root` pointing to a writable fixture directory. The native report
itself records the bootstrap result.

Leave space for the installed runtime, model downloads, and the Windows
pagefile in addition to compiler outputs. Windows CPU Whisper uses bfloat16
with PyTorch 2.5+ to keep word-timestamp attention buffers within memory;
NLLB uses safetensors 0.8's streaming reads to avoid full-file copy-on-write
memory reservations. These runtime choices are Windows-only.

The Bazel-native Python test extension is Unix-only. On Windows, use
`just batchalign pytest-wheel <disposable-python.exe> -k <test-expression>`
with a Python interpreter from a bootstrapped test sidecar. This builds the
wheel through Bazel, installs it and the locked pytest into that disposable
interpreter, and collects tests without importing the source-tree package.

## Code organization

- `crates/batchalign/batchalign-core` owns pipeline domain types, task runners,
  CHAT-facing transformations, and backend protocols.
- `crates/batchalign/batchalign-engine` owns dispatch, bounded batching, cache,
  pipeline execution, and PyO3 integration.
- `python/batchalign` owns Python backends, recipes, worker processes, and CLI.
- `apps/batchalign` owns the desktop application.

Keep modules conceptual, APIs narrow, and backend submission bounded. Do not
add compatibility namespaces for normal Batchalign behavior: reusable domain
logic belongs in Batchalign core, while orchestration glue belongs in task
runners or the engine.

## Testing changes

Use focused tests while iterating. Before handoff, run the relevant Batchalign
Bazel test scope. Corpus and parity checks should use small chunks with the
task cache cleared between implementation flips. The parity runner under
`scripts/parity` enforces bounded workers and monitors resident memory.

When changing CHAT output, add explicit input and gold fixtures. Production
code must use typed Chatter construction and validation instead of weakening a
validator or assembling tiers as strings.
