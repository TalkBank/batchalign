# Install or update Batchalign

These instructions install the command-line application and its backend extras.
The installer also installs `uv` if needed and selects Python 3.11 for Batchalign.

## macOS or Linux

Open Terminal, paste this command, and press Enter:

```bash
curl -LsSf https://raw.githubusercontent.com/TalkBank/batchalign/main/bootstrap/bootstrap.sh | sh
```

## Windows

Open PowerShell, paste this command, and press Enter:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-Expression ((Invoke-WebRequest -UseBasicParsing 'https://raw.githubusercontent.com/TalkBank/batchalign/main/bootstrap/bootstrap.ps1').Content)"
```

## Check the installation

Close and reopen your command window, then run:

```bash
batchalign --help
batchalign version
```

You should see a list of commands and version information. Continue to the
[Quick Start](quick-start.md) for your first processing task. If the command
cannot be found, see [Troubleshooting](troubleshooting.md).

## Update an existing installation

Run the same installer again. It upgrades the `batchalign[all]` tool installation
with prereleases allowed, matching the repository's bootstrap scripts.

For an existing `uv` installation, the equivalent command is:

```bash
uv tool install --upgrade --python=3.11 --prerelease=allow 'batchalign[all]>=0.10'
```

The package on PyPI is named `batchalign`. It installs the `batchalign` command.
Model files may download separately when you first use a backend; see [Model downloads](model-downloads.md).
