# Package and release surfaces

| Surface | Source of truth |
|---|---|
| Python distribution name, version, dependencies, scripts | `python/pyproject.toml` (`batchalign`) |
| Rust workspace version and dependencies | Root `Cargo.toml` |
| Native wheel matrix | `.github/workflows/publish-pypi.yml` |
| Installed wheel smoke checks | `.github/workflows/bazel-wheels.yml` |
| Desktop bundle | `apps/batchalign/batchalign-gui/` and its Bazel targets |
| HTTP service | `python/batchalign/api.py`, `cli/daemon.py` |

The Python distribution provides the CLI, Python API, and compiled engine.
A desktop bundle and a Python wheel are separate artifacts. Their versions and
release procedures should not be inferred from obsolete server-era version tables.

For the release procedure, see [Release the Python package](release-checklist.md).
