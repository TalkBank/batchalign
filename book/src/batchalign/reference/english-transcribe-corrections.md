# English ASR text corrections

The Rust ASR cleanup code applies English-specific orthographic rules when the
language is `eng`:

| Rule | Example |
|---|---|
| Capitalize the pronoun and supported contractions | `i` → `I`, `i'm` → `I'm` |
| Strip periods from an allowlist of abbreviations | `Dr.` → `Dr` |
| Capitalize the first eligible word of an utterance | `hello world .` → `Hello world .` |

These modify spelling directly; they do not add a CHAT replacement annotation.
The abbreviation rule runs before token splitting so a title's period is not
mistaken for an utterance boundary. It is an allowlist, not a general instruction
to strip periods from arbitrary words or numbers.

The authoritative surfaces and exclusions are in
`crates/batchalign/batchalign-core/src/asr/cleanup.rs`, including
`EN_I_CAP_REWRITES`, `EN_TITLE_PERIOD_SURFACES`, and the pre/post-retokenization
English correction functions. Their invocation order is in `asr/prepare.rs`
and the ASR assembly path.
