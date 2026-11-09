# Documentation scope and maintenance

This book documents the products present in the Batchalign repository:
the Python CLI and backends, Rust core and engine, HTTP service, and desktop
application. The workspace membership in `Cargo.toml`, Python command registry,
`just` recipes, and release workflows are the implementation references.

## Current organization

- Tutorials introduce a first Batchalign workflow.
- How-to guides cover user tasks and contributor workflows.
- Reference pages describe commands, data contracts, and CHAT notation.
- Explanations describe the current pipeline and runtime.
- [Related tools](../../related-tools.md) identifies the separately maintained
  Chatter, CLAN, and editor documentation.

The old CLAN, Chatter, VS Code, parser-development, and combined-toolchain
operations manuals have been removed. They described products or source paths
that are no longer in this repository. Consolidated Batchalign pages are HTML
redirects rather than duplicate chapters or a large previous-locations menu.
Historical research is linked from [Historical studies and decisions](historical-notes.md).

## Maintaining the book

Edit `book/src/SUMMARY.md` when adding or reorganizing chapters. Update incoming
links when consolidating a page, and add an `output.html.redirect` entry in
`book/book.toml` for a retired published URL. Link to the owning project's
documentation for external products instead of copying their install or release
instructions into this book.

Validate with `just docs build` and `just docs linkcheck`. The Bazel-backed recipes
provide the configured mdBook, Mermaid, and link-check tools. Compare examples
against `just batchalign cli COMMAND --help`; model accuracy claims require
separate measurements and must identify their fixtures and environment.
