# Release the Python package

1. Set the Python package version in `python/pyproject.toml`. The repository
   wrapper refreshes `python/uv.lock`; check the resulting diff. Rust workspace
   and desktop versions have separate owners.
2. Run [the relevant checks](testing.md), inspect their results, and record any
   known baseline failures separately from regressions.
3. Commit the intended release state and push it to the branch CI will build.
4. Dispatch `.github/workflows/publish-pypi.yml` with `tag` exactly matching the
   Python version. The workflow builds native macOS ARM/Intel, Linux ARM/x86-64,
   and Windows x86-64 wheels.
5. Verify that every artifact came from the intended commit, has the expected
   version/platform tag, and passes `bazel/python/verify_wheel.py` and `twine check`.
6. Publish through the configured channel. The workflow's `publish=true` route
   requires PyPI trusted publishing. If that is not configured, build with
   `publish=false`, download all five wheel artifacts, and upload them using
   authenticated Twine.
7. Verify PyPI's file list and hashes against the artifacts you uploaded.

Do not publish local development wheels in place of the matrix artifacts.
The exact workflow and package metadata are the release contract; historical
`batchalign3` distribution and Rust-server release instructions do not apply.
