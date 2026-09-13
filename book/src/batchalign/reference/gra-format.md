# Dependency tiers (`%gra`)

A `%gra` item has the form `index|head|relation`. It describes the grammatical
relation of one morphology unit to its head. Index 0 in the head position denotes
the root convention used by the current backend output.

The Stanza renderer supplies structured indices, heads, and relation labels.
The Rust morphology runner constructs typed grammatical relations and aligns
`%mor` and `%gra` using TalkBank model alignment helpers before committing tiers.
A rejected candidate can leave an utterance without new analysis and emit a warning.

The number of dependency units is not necessarily the number of whitespace-
separated main-tier tokens: morphology can include clitic components. Consult
[the morphology contract](morphosyntax.md) and the shared
[dependent-tier reference](../../chat-format/dependent-tiers.md).

Source: `python/batchalign/backends/morphosyntax/ud/render.py` and
`crates/batchalign/batchalign-core/src/taskrunners/morphosyntax.rs`.
