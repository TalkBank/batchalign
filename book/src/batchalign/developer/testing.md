# Test a Batchalign change

Run commands from the repository root using `just`.

| Check | Command | Scope |
|---|---|---|
| Product tests | `just batchalign test` | Core Rust targets, explicitly named engine tests, Python pytest target |
| Python tests | `just batchalign pytest` | Python suite through Bazel; extra arguments are forwarded to pytest |
| Type/lint checks | `just batchalign lint` | Mypy, followed by Ruff when available |
| GUI integration | `just batchalign gui test` | Playwright against the Bazel-built PyApp service, with Tauri APIs stubbed |
| Book and links | `just docs build` | mdBook HTML and configured linkcheck renderer |

For a focused Python case:

```bash
just batchalign pytest -k cli_input_list
```

For an integration check, use the real development entrypoint:

```bash
just batchalign cli --parallel 2 morphotag /path/to/fixtures -o /tmp/tagged-check
```

Choose inputs that exercise the behavior being changed. For inference changes,
compare semantic outputs as well as elapsed time and RSS; record cache state and
model settings. Tests with fake backends check orchestration, not model accuracy.

The product recipe explicitly includes engine unit, cache-smoke, and
pipeline-smoke targets that a broad wildcard can omit because of manual tags.
The wheel CI matrix also checks native platform packaging and Python 3.10 imports.

GUI checks need a browser installed for the pinned Playwright version. On a cold
machine, the bundled runtime may need first-launch setup before it can serve
requests. Distinguish setup failures from frontend assertions when diagnosing
results.
