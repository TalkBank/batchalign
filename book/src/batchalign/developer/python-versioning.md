# Python versions and wheel tags

`python/pyproject.toml` declares Python `>=3.10`. The extension uses CPython's
stable ABI, with release wheels tagged `cp310-abi3` for each supported platform.
The wheel CI smoke test installs and imports the package on Python 3.10.

The user bootstrap scripts select Python 3.11 for `batchalign[all]`. This is
separate from the minimum version supported by the core wheel. Optional model
libraries can impose additional interpreter or platform constraints.

Use the bootstrap-selected interpreter for the documented end-user installation.
A stable-ABI tag is not a claim that every model extra works on every newer or
free-threaded Python build. See `python/pyproject.toml`, `bootstrap/`, and the
wheel workflows before changing interpreter support.
