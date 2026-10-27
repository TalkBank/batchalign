set shell := ["bash", "-c"]
set positional-arguments := true

# Build static HTML.
build:
    bazel run //book:html

serve port="3000":
    bazel run //book:serve -- --port "{{port}}" --dest-dir "build/preview-{{port}}"

linkcheck:
    bazel run //book:linkcheck

# One-time installation of the book tools (mdBook 0.5-compatible plugins).
setup:
    cargo install --locked mdbook@0.5.2 mdbook-mermaid@0.17.1 mdbook-linkcheck2@0.11.0
