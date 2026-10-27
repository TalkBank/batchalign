set shell := ["bash", "-c"]
set positional-arguments := true

# Build static HTML.
build:
    bazel run //book:html

serve port="3000":
    bazel run //book:serve -- --port "{{port}}" --dest-dir "build/preview-{{port}}"

linkcheck:
    bazel run //book:linkcheck

# Fetch/build the same Bazel-managed tools used by build and serve.
setup:
    bazel build @multitool//tools/mdbook @multitool//tools/mdbook-mermaid //bazel/book:linkcheck_tool
