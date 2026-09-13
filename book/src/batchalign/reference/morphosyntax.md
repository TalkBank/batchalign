# Morphosyntax processing contract

The `morphotag` pipeline adds typed `%mor` and `%gra` tiers. Its implementation
spans the Rust runner and Python Stanza backend; linguistic rendering is not
entirely Rust-owned.

## Input and language

The Rust runner reads CHAT, skips Conversation Analysis files marked
`@Options: CA`, and collects utterances that need analysis. Language comes from
`@Languages:` with utterance-level overrides such as `[- hin]` where applicable.
The CLI has no morphotag `--lang` option.

By default, the CLI stages copies with existing `%mor` and `%gra` removed before
parsing. `--keep-existing` leaves them in place for the runner's already-tagged
check. Clearing tiers does not bypass the backend result cache.

## Backend processing

`python/batchalign/backends/morphosyntax/stanza.py` groups batch requests by
language configuration. It prepares text, runs Stanza, and uses the Python
`ud/tokenize.py` and `ud/render.py` modules for token handling and structured
morphological/dependency output. The `ud/` language modules contain additional
language-specific behavior.

Preserve mode installs a tokenizer postprocessor to reconcile Stanza tokenization
with the input. `--retokenize` selects the other mode and permits changes to word
boundaries. The backend's identity includes the mode and its rendering contract.
Do not treat a model's raw token count as the CHAT main-tier word count.

A failed batched model call can fall back to individual sentence processing.
Pipeline initialization failures propagate as backend failures; an unsupported
or broken model is not treated as a successful empty analysis for the whole file.

## Applying results

The Rust runner converts the structured backend output into TalkBank model
objects, aligns morphology and dependency tiers with `try_align_mor_gra`, and
checks the candidate against the main tier before committing it. An utterance
whose analysis cannot be aligned can be skipped with a warning; a completed file
is not a guarantee that every utterance received new analysis.

`%gra` unit indices, heads, and relations originate in the backend output. The
runner constructs typed relations and the CHAT writer serializes them. Avoid
attributing current dependency-tree behavior to the retired server's
`build_gra_and_validate` path.

## Scheduling and reuse

The per-file dispatch window is 128 utterances. Stanza's default engine batch
maximum is 128 with a 100 ms collection window. Result caching is enabled.
See [Performance](../user-guide/performance.md) and [Caching](../user-guide/caching.md).

## Source locations

| Concern | Source |
|---|---|
| CLI staging and options | `python/batchalign/cli/morphotag.py` |
| Extraction, dispatch, typed injection | `crates/batchalign/batchalign-core/src/taskrunners/morphosyntax.rs` |
| Protocol and cache-key fields | Core `proto/morphosyntax.rs` |
| Stanza configuration and batching | `python/batchalign/backends/morphosyntax/stanza.py` |
| Token reconciliation and rendering | Python backend `ud/tokenize.py`, `ud/render.py`, language submodules |

For a processing walkthrough, see [Add morphology and grammar](../user-guide/commands/morphotag.md).
