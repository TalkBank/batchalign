#!/usr/bin/env bash
# Test the Bazel-built Windows wheel in a disposable, bootstrapped sidecar
# interpreter. Installs the wheel and the locked pytest into that interpreter.
set -euo pipefail
case "$(uname -s)" in
    MINGW*|MSYS*|CYGWIN*) ;;
    *) echo "pytest_windows_wheel.sh requires Windows" >&2; exit 2 ;;
esac
source "${BUILD_WORKSPACE_DIRECTORY}/bazel/python/runfiles_resolve.sh"
# Bzlmod rootpaths prefix external repositories with ../, while Windows
# manifest keys start directly with the canonical repository name.
UV="$(runfiles_resolve "${1#../}")"
WHEEL="$(runfiles_resolve "$2")"
TAG="$(runfiles_resolve "$3")"
shift 3
if [[ $# -lt 1 ]]; then
    echo "usage: just batchalign pytest-wheel <disposable-python.exe> [pytest arguments]" >&2
    exit 2
fi
PYTHON="$1"; shift
workspace="$BUILD_WORKSPACE_DIRECTORY"
test_dir="$(mktemp -d "${TMPDIR:-/tmp}/batchalign-wheel-test.XXXXXX")"
wheel_name="$(cat "$TAG")"
cp "$WHEEL" "$test_dir/$wheel_name"
pytest_requirement="$(sed -n 's/^\(pytest==[^ ]*\).*/\1/p' "$workspace/python/requirements.lock.txt")"
[[ -n "$pytest_requirement" ]] || { echo "Missing pytest lock entry" >&2; exit 2; }
"$UV" pip install --python "$PYTHON" --no-deps --reinstall "$test_dir/$wheel_name"
"$UV" pip install --python "$PYTHON" "$pytest_requirement"
# Isolated Python + importlib collection prevent the source checkout from
# shadowing the installed wheel (and its packaged .pyd extension).
cd "$test_dir"
echo "Testing installed wheel with $PYTHON; evidence directory: $test_dir"
BATCHALIGN_TEST_INSTALLED_WHEEL=1 "$PYTHON" -I "$workspace/bazel/python/pytest_windows_wheel.py" \
    --import-mode=importlib -c "$workspace/python/pytest.ini" \
    --junitxml="$test_dir/results.xml" "$workspace/python/batchalign/tests" "$@"
