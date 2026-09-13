# French processing reference

The transcription language code is `fra`. For morphology, use the appropriate
CHAT `@Languages:` header; there is no morphotag `--lang` option.

French-specific rendering helpers are in `python/batchalign/backends/morphosyntax/ud/fr/`. Include contractions and clitic elisions in a review sample.

Language resolution and processor selection are defined in
`python/batchalign/backends/morphosyntax/ud/lang.py` and `stanza.py`.
Backend availability and linguistic quality must be checked for the actual model
and input; a recognized language code alone is not a support guarantee.

See [Language selection](../language-handling.md),
[Morphosyntax](../morphosyntax.md), and [CLI reference](../../user-guide/cli-reference.md).

The [earlier French study](https://github.com/TalkBank/batchalign/blob/fbaee727d9649f8d4bf1592433fb71f7acce7b12/book/src/batchalign/reference/languages/french.md)
contains model probes and implementation notes from a previous architecture.
Its measurements and mitigation claims have not been revalidated by this documentation update.
