# Why one word can have several morphology units

A written contraction can represent several grammatical units. Stanza may
represent it as a multi-word token, while CHAT represents morphological components
within the analysis of a main-tier word. These counts must not be confused.

The current backend reconciles token boundaries and renders structured units;
the Rust runner aligns the resulting `%mor`/`%gra` tiers to the CHAT main tier.
See [Morphosyntax processing](morphosyntax.md) for ownership and failure handling.

Retokenization is a separate choice about main-tier word boundaries. Use
`--retokenize` only when you want that mode, and review its effect on the transcript.
