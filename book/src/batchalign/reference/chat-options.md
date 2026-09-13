# CHAT options that affect processing

| Header option | Current runner behavior |
|---|---|
| `@Options: CA` | Morphosyntax skips Conversation Analysis transcripts |
| `@Options: NoAlign` | Forced alignment skips the transcript |

These are task-specific checks, not a universal skip directive for every command.
The CLI's default morphology staging also removes the obsolete exact header
`@Options:\tmulti` along with old `%mor`/`%gra` tiers.

Source: core `taskrunners/morphosyntax.rs`, `taskrunners/fa.rs`, and
`python/batchalign/cli/morphotag.py`.
