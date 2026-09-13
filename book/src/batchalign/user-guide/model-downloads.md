# Prepare model downloads

Use this guide before processing on a new computer or before taking a machine
offline.

1. Install the backend dependencies using the [standard installer](installation.md).
2. While connected to the internet, run a small representative input with the
   same command, language, engine, and model you intend to use later.
3. Let the command complete. A successful installation alone does not prove that
   all required models have downloaded.
4. Repeat for other languages or models you plan to use. A Stanza model for one
   language does not cover every language.
5. If you need offline operation, test the exact command and input type after
   disconnecting. Cloud engines still require their external services.

Downloads and disk locations are managed by each backend's model libraries.
Download sizes vary; there is no fixed total size for a Batchalign installation.
The current CLI has no model-download or cache-prewarm subcommand.

The Stanza morphosyntax backend refreshes an existing resource catalog once per
process, retaining the cached catalog if refresh fails. It loads language pipelines
lazily unless a language is pinned at construction. Missing model files can still
require downloads. See [Performance](performance.md) for the distinction between
model files on disk, loaded models in memory, and cached task results.
