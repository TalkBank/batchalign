# Wheel platform reference

The current Python wheel workflows build these native platforms:

| Platform | CI runner |
|---|---|
| macOS ARM64 | `macos-14` |
| macOS x86-64 | `macos-15-intel` |
| Linux x86-64 | `ubuntu-latest` |
| Linux ARM64 | `ubuntu-24.04-arm` |
| Windows x86-64 | `windows-latest` |

The extension wheel uses `cp310-abi3`. Linux builds target manylinux 2.28 through
the wheel builder. The wheel smoke matrix installs and imports on Python 3.10.
Optional model libraries can have narrower platform support than the core wheel.

The bootstrap scripts select Python 3.11 and install `batchalign[all]`. Desktop
bundles are separate artifacts. See [Install Batchalign](../user-guide/installation.md)
and [Package and release surfaces](../developer/release-contract.md).

Source: `.github/workflows/publish-pypi.yml`, `bazel-wheels.yml`, and
`python/pyproject.toml`.
