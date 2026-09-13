# Italian processing reference

The transcription language code is `ita`. For morphology, use the appropriate
CHAT `@Languages:` header; there is no morphotag `--lang` option.

Italian handling spans `ud/it/`, the shared tokenizer, and renderer. The backend identity currently includes its native-MWT rendering contract; old Rust reconciler tables are not the current source map.

Language resolution and processor selection are defined in
`python/batchalign/backends/morphosyntax/ud/lang.py` and `stanza.py`.
Backend availability and linguistic quality must be checked for the actual model
and input; a recognized language code alone is not a support guarantee.

See [Language selection](../language-handling.md),
[Morphosyntax](../morphosyntax.md), and [CLI reference](../../user-guide/cli-reference.md).

The [earlier Italian study](https://github.com/TalkBank/batchalign/blob/fbaee727d9649f8d4bf1592433fb71f7acce7b12/book/src/batchalign/reference/languages/italian.md)
contains model probes and implementation notes from a previous architecture.
Its measurements and mitigation claims have not been revalidated by this documentation update.
