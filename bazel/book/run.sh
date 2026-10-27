#!/usr/bin/env bash
# Resolve all documentation tools from Bazel runfiles before entering the book.
# --- begin runfiles.bash initialization v3 ---
set -uo pipefail; set +e; f=bazel_tools/tools/bash/runfiles/runfiles.bash
source "${RUNFILES_DIR:-/dev/null}/$f" 2>/dev/null || \
  source "$(grep -sm1 "^$f " "${RUNFILES_MANIFEST_FILE:-/dev/null}" | cut -f2- -d' ')" 2>/dev/null || \
  source "$0.runfiles/$f" 2>/dev/null || \
  source "$(grep -sm1 "^$f " "$0.runfiles_manifest" | cut -f2- -d' ')" 2>/dev/null || \
  { echo >&2 "ERROR: cannot find $f"; exit 1; }; f=; set -e
# --- end runfiles.bash initialization v3 ---

command="$1"
mdbook="$(rlocation "$2")"
mermaid="$(rlocation "$3")"
linkcheck="$(rlocation "$4")"
shift 4
for tool in "$mdbook" "$mermaid" "$linkcheck"; do
    [[ -x "$tool" ]] || { echo "Missing Bazel book tool: $tool" >&2; exit 1; }
done
# Preprocessors and renderers are launched by name by mdBook.
export PATH="$(dirname "$mermaid"):$(dirname "$linkcheck"):$PATH"
cd "$BUILD_WORKSPACE_DIRECTORY/book"
if [[ "$command" == serve ]]; then
    exec "$mdbook" serve --open "$@"
fi
exec "$mdbook" "$command" "$@"
