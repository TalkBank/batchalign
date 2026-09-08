#!/bin/sh

set -eu

if ! command -v uv >/dev/null 2>&1; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
    export PATH
fi

if ! command -v uv >/dev/null 2>&1; then
    echo "uv was installed, but it is not available on PATH." >&2
    echo "Start a new shell and rerun this script." >&2
    exit 1
fi

batchalign_requirement='batchalign[all]>=0.10'
installed_tools=$(uv tool list) || {
    echo "Unable to inspect installed uv tools." >&2
    exit 1
}

if printf '%s\n' "$installed_tools" | grep -Eq '^batchalign v[^[:space:]]+'; then
    echo "Upgrading batchalign[all]..."
    uv tool install --upgrade --python=3.11 --prerelease=allow "$batchalign_requirement"
else
    echo "Installing batchalign[all]..."
    uv tool install --python=3.11 --prerelease=allow "$batchalign_requirement"
fi

echo "Batchalign is ready."
