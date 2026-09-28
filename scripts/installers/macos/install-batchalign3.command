#!/bin/bash
# install-batchalign3.command — One-click Batchalign installer for macOS.
#
# Double-click this file in Finder to install Batchalign.
# It installs the uv package manager (if needed) and then installs batchalign.
#
# After installation, open a new Terminal window and type:
#   batchalign --help
#
# Environment variables (for testing / internal use):
#   BATCHALIGN_PACKAGE  Override the package spec. Can be a PyPI name (default:
#                       "batchalign"), a local wheel path, or a PEP 508 URL.
#   CI                  When set to "true", skips interactive prompts.

set -euo pipefail

BATCHALIGN_PACKAGE="${BATCHALIGN_PACKAGE:-batchalign}"

echo "============================================"
echo "  Batchalign Installer for macOS"
echo "============================================"
echo ""

# --------------------------------------------------------------------------
# Step 1: Check for / install uv
# --------------------------------------------------------------------------
if command -v uv &>/dev/null; then
    echo "[OK] uv is already installed: $(uv --version)"
else
    echo "[...] Installing uv package manager..."
    curl -LsSf https://astral.sh/uv/install.sh | sh

    # Source the shell profile so uv is available in this session.
    # uv installs itself to ~/.local/bin or ~/.cargo/bin depending on the
    # platform; the install script updates the appropriate profile.
    for profile in "$HOME/.zshrc" "$HOME/.bashrc" "$HOME/.profile" "$HOME/.zprofile"; do
        if [ -f "$profile" ]; then
            # shellcheck disable=SC1090
            source "$profile" 2>/dev/null || true
        fi
    done

    # Also try the common install locations directly.
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

    if ! command -v uv &>/dev/null; then
        echo ""
        echo "[ERROR] uv was installed but is not on PATH."
        echo "Close this window, open a new Terminal, and run:"
        echo "  uv tool install batchalign"
        echo ""
        [ "${CI:-}" = "true" ] || read -rp "Press Enter to close..."
        exit 1
    fi

    echo "[OK] uv installed: $(uv --version)"
fi

echo ""

# --------------------------------------------------------------------------
# Step 2: Install or upgrade batchalign
# --------------------------------------------------------------------------
if uv tool list 2>/dev/null | grep -q "^batchalign "; then
    echo "[...] Upgrading batchalign..."
    uv tool install --force --python 3.12 "$BATCHALIGN_PACKAGE"
else
    echo "[...] Installing batchalign (this may take a minute)..."
    uv tool install --python 3.12 "$BATCHALIGN_PACKAGE"
fi

echo ""

# --------------------------------------------------------------------------
# Step 3: Verify
# --------------------------------------------------------------------------
# uv tool install puts binaries in ~/.local/bin.
export PATH="$HOME/.local/bin:$PATH"

if command -v batchalign &>/dev/null; then
    echo "[OK] batchalign is installed!"
    echo ""
    batchalign --version 2>/dev/null || true
    echo ""
    echo "============================================"
    echo "  Installation complete!"
    echo ""
    echo "  Open a NEW Terminal window and run:"
    echo "    batchalign --help"
    echo ""
    echo "  First-time setup (for transcription):"
    echo "    batchalign setup"
    echo "============================================"
else
    echo ""
    echo "[WARNING] batchalign installed but not found on PATH."
    echo "Close this window, open a new Terminal, and try:"
    echo "  batchalign --help"
fi

echo ""
[ "${CI:-}" = "true" ] || read -rp "Press Enter to close..."
