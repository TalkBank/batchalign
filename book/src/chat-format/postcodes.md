# Postcodes (`[+ ...]`)

**Status:** Reference
**Last updated:** 2026-05-11 23:01 EDT

A **postcode** is a tagged annotation token that attaches to an
*utterance as a whole* and appears after the terminator. The
canonical CHAT syntax is `[+ <text>]`. Postcodes carry researcher /
analysis tags about the utterance — whether it should be excluded
from analysis, how it should be coded, what kind of speech act it
represents — without modifying the utterance's word content.

## Syntax and Scope

```text
*CHI:   I want cookie .  [+ exc]
*MOT:   what did you say ?  [+ imp]
*CHI:   no I don't want it !  [+ neg] [+ trn]
```

Three structural facts to internalize:

1. **Postcodes attach to the utterance, not to a word.** They sit
   after the terminator, on the main tier, alongside (but distinct
   from) any utterance-level bullet. Unlike word-scoped annotations
   (`[: ...]` replacement, `[% ...]` comment, `[= ...]` explanation,
   `[* ...]` error code), a postcode does not modify the
   interpretation of any single word — it tags the whole utterance.
2. **Multiple postcodes may follow a single terminator.** They are
   ordered, but the order is not semantically privileged.
3. **The body is free-form text.** The CHAT word grammar is *not*
   applied to postcode contents. Researchers can write arbitrary
   tags, codes, descriptions, comments, or analytic notes. The model
   stores the raw text and leaves interpretation to downstream
   tooling and conventions.

## Common Postcodes — Empirical Survey

The postcode vocabulary is **open-ended**: the CHAT format imposes no
closed set, and an audit of every `[+ ...]` token across a
JSON-mirrored snapshot of the TalkBank corpora (~99k files, 23+
data-repo families) found **488 distinct values** in active use.

The findings split into three tiers ranked by *repo spread* (in how
many distinct corpus families the code appears) — the more useful
ranking than raw count, because high-count codes can be concentrated
in a single corpus.

### Tier 1 — Cross-corpus codes (in 7+ repos)

These are the conventions every CHAT consumer should expect to
encounter across collections:

| Postcode | Repo spread | Total occurrences | Meaning |
|---|---|---|---|
| `[+ gram]` | 13 | ~3,100 | Grammatical — utterance is grammatically well-formed for purposes of the analysis. |
| `[+ exc]` | 9 | ~26,900 | Exclude utterance from analysis. The utterance is preserved in the transcript but tagged so analytic tools (CLAN's `freq`, `mlu`, etc.) skip it. |
| `[+ bch]` | 9 | ~10,000 | Backchannel — listener-side acknowledgement (`mhm`, `yeah`) that should not be counted as a substantive turn. |
| `[+ trn]` | 7 | ~3,800 | Translation utterance. |

### Tier 2 — Multi-corpus protocol codes (in 4-6 repos)

Codes deployed across several CHILDES sub-collections, typically
encoding picture-narration / story-reading / imitation experimental
conditions. Substantial raw counts (often tens of thousands), but
their meaning is set by the originating protocol — consult per-corpus
documentation rather than assuming a global definition:

| Postcode | Repo spread | Total occurrences |
|---|---|---|
| `[+ SR]` | 5 | ~31,000 |
| `[+ IN]` | 5 | ~24,500 |
| `[+ PI]` | 5 | ~22,700 |
| `[+ R]` | 4 | ~16,200 |
| `[+ I]` | 4 | ~10,500 |
| `[+ nv]` | 4 | ~3,300 |
| `[+ imit]` | 4 | ~3,200 |

### Tier 3 — Single-corpus and long-tail codes

About 80% of the 488 distinct values appear in one repo only. The
single-corpus codes include high-volume protocol vocabularies (e.g.
`[+ uncued]` ~19,500 in one repo, `[+ NAC]` ~3,500 in one repo,
`[+ diary]` ~2,800 in a Romance/Germanic diary-study collection,
`[+ noatt]` ~2,300 in one repo, `[+ inter-utter-switch]` ~720
flagging code-switching turns).

The long tail also includes researcher-private notes, typos that
survived `check`, and per-study coding schemes. Tooling MUST treat
any unknown postcode value as opaque text — the corpus author may
know what it means, the format does not.

### Caveats

- Numbers are from a snapshot audit and will drift as corpora are
  added or revised. Treat the broad shape (open vocabulary, ~4 truly
  cross-corpus codes, ~10 multi-corpus protocol codes, ~hundreds of
  single-corpus or long-tail codes) as the load-bearing finding, not
  the exact counts.
- "Repo spread" counts data-repo families, not individual files.
  Two corpora curated by the same group inside one data-repo count
  as one for spread; researchers using the same code in two
  different family-of-corpora packages count as two.
- The CHAT manual remains the source of truth for *standard*
  conventions. The empirical survey above shows what is *actually*
  deployed; when ingesting a new corpus, consult its own
  documentation for the postcodes in use.

## What Postcodes Are NOT

Postcodes are easy to confuse with several other CHAT annotation
forms because they all use square brackets. The differences are
substantive and load-bearing.

| Form | Scope | Body validation | Purpose |
|---|---|---|---|
| `[+ ...]` | **Utterance-level** (this doc) | None — free text | Researcher / analysis tag attached to the whole utterance |
| `[: ...]` | **Word-level** | Replacement words ARE validated as CHAT words | Sanctioned-form correction of the preceding word (see `replacements.md`) |
| `[% ...]` | **Word-level** | None — free text | Free-form comment about the preceding word or local span |
| `[= ...]` | **Word-level** | None — free text | Explanation of unclear / non-standard speech (often paired with `xxx` / `yyy` placeholders) |
| `[* ...]` | **Word-level** | None — error code text | Error coding for the preceding word, optionally with a structured code |

Two consequences worth pinning down explicitly:

- **A postcode cannot carry per-word semantics.** If you want to
  attach a comment, replacement, or error code to a single word, use
  the appropriate word-scoped form. Stretching a postcode to mean
  "this word is X" loses the per-word position downstream tools
  depend on.
- **A word-scoped annotation cannot tag an utterance.** If you want
  to mark an entire utterance for exclusion or translation, use a
  postcode. A `[% exclude this]` after a word does not mean "exclude
  the utterance" to any consumer.

## Not postcodes: quotation markers

Quotation terminators and linkers such as `+"` are separate from `[+ ...]`
postcodes. See [Utterance terminators](utterances.md#terminators).
Do not use a word annotation or a quotation marker as an utterance-level tag.

## Preserving postcodes

Keep utterance-level postcodes when editing a transcript. Downstream analysis
tools interpret the code values according to their own protocols; a Batchalign
processing run is not a CLAN analysis command.

For parsing and validation implementation details, see
[Chatter](../related-tools.md#chatter-and-chat-format-tools).
