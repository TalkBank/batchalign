#!/usr/bin/env bash
# Compile pinned source with Bazel's Cargo/rustc; never install into the host.
set -euo pipefail
output="$PWD/$1"
source_dir="$(cd "$(dirname "$2")" && pwd)"
for file in $BOOK_RUST_FILES; do
    case "$file" in
        */bin/cargo|*/bin/rustc)
            export PATH="$(cd "$(dirname "$file")" && pwd):$PATH"
            ;;
    esac
done
build_dir="$(mktemp -d "${TMPDIR:-/tmp}/mdbook-linkcheck.XXXXXX")"
trap 'rm -rf "$build_dir"' EXIT
cp -R "$source_dir/." "$build_dir/src"
chmod -R u+w "$build_dir/src"
cargo build --locked --release --manifest-path "$build_dir/src/Cargo.toml" --target-dir "$build_dir/target"
cp "$build_dir/target/release/mdbook-linkcheck2" "$output"
chmod +x "$output"
