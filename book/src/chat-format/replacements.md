# Replacements

**Status:** Current
**Last updated:** 2026-05-11 23:14 EDT

A **replacement** is a CHAT annotation `[: ...]` that pairs a single
spoken word on the main tier with one or more "intended" words. It
records both what the speaker actually said and what the analysis should
treat the utterance as containing.

```chat
*CHI:	wanna [: want to] go .
*CHI:	dis [: this] is fun .
*CHI:	rocking+house [: rocking+horse] [*] ?
```

This page is the canonical reference for what replacements mean in
TalkBank — both as a CHAT-manual construct and as a typed AST in this
repo. The most important load-bearing fact, which the rest of the page
expands on:

> **Replacements are word-level, not group-level. Each tier domain
> chooses *one* side of the pair: `%mor` analyzes the replacement
> (right side); `%wor`, `%pho`, `%sin` align to the original (left
> side). `%gra` follows `%mor`.**

## CHAT Syntax

### Word-Level Scope

A replacement attaches to a single `standalone_word` on the main tier
and contains one or more replacement words inside the brackets:

```chat
*CHI:	gonna [: going to] eat lunch .
*CHI:	dis [: this] toy .
*CHI:	rocking+house [: rocking+horse] [*] ?
```

Replacement words can be separated
by whitespace, so `[: going to]` is a single replacement of `gonna`
with two words.

### There Is No Group-Level Replacement

`<dat is> [: that is]` is **not** valid CHAT. A replacement does not
attach to a group; it attaches to a single word. The grammar enforces
this by typing: `ReplacedWord.word: Word`, never `Group`. To replace
words inside a group, attach the replacement to the inner word:

```chat
*CHI:	<dat [: that] is> [/] is broken .
```

This shape — replacement inside a group inside a retrace — is legal
because each annotation operates at its own scope.

### There Is No `[::]` Form

Some literature on CHILDES tooling references a `[::]` annotation; it
does **not** exist in this repo's grammar, parser, or model, and is not
defined by the current CHAT manual. Only `[:]` exists. If you encounter
`[::]` in legacy data, treat it as a parse error to investigate, not a
construct to support.

## The Per-Domain Alignment Rule

This is the rule contributors most often get wrong. Different tier
domains align to different sides of a replacement pair:

| Tier | Side aligned to | Rationale |
|------|----------------|-----------|
| `%mor` | **replacement** (right) | Morphosyntactic analysis annotates the *target* form, not the error |
| `%gra` | **replacement** (right) | Grammatical relations align to `%mor`'s structure |
| `%wor` | **original** (left) | Word-level timing is for what was actually spoken |
| `%pho` | **original** (left) | Phonological transcription describes what was actually spoken |
| `%sin` | **original** (left) | Spelling-in-actual describes the original surface form |

The mnemonic: **the replacement encodes the intended form** (what the
speaker meant or what a corrected transcript would read). Tiers
analyzing intent (`%mor`/`%gra`) use the replacement; tiers
documenting realization (`%wor`/`%pho`/`%sin`) use the original.

```mermaid
flowchart LR
    spoken["Original word\n(left of [:)\n'dis'"]
    target["Replacement words\n(inside [: ])\n'this'"]

    spoken -->|"%wor (timing)"| wor["%wor: dis"]
    spoken -->|"%pho (phonology)"| pho["%pho: dɪs"]
    spoken -->|"%sin (spelling)"| sin["%sin: dis"]
    target -->|"%mor (UD parse)"| mor["%mor: pron|this"]
    target -->|"%gra (paired with %mor)"| gra["%gra: 1|0|ROOT"]
```

For multi-word replacements like `gonna [: going to]`, the rule
generalizes consistently:

- `%wor` / `%pho` / `%sin` produce **one** entry — for `gonna`.
- `%mor` produces **two** entries — for `going` and `to`.
- `%gra` produces **two** entries — paired to the two `%mor` items.

The full table of per-domain rules is in
[`resources/spec/docs/ALIGNMENT_RULES.md`](https://github.com/TalkBank/batchalign/blob/main/resources/spec/docs/ALIGNMENT_RULES.md).

## Interactions with Other Annotations

### Replacements and Retraces Are Orthogonal

A retrace (`[/]`, `[//]`, `[///]`, `[/-]`) and a replacement
(`[:]`) are distinct annotations operating at different structural
levels:

- Retraces wrap **content** (a single word or a group). They are first-
  class `UtteranceContent` variants and represent post-hoc speaker
  correction.
- Replacements attach **inside** a `Word` slot via `ReplacedWord`. They
  are editorial metadata about an individual spoken word.

Both can coexist:

```chat
*CHI:	<dat [: that] is> [/] is broken .   (replacement inside retrace)
```

A retrace cannot live *inside* a replacement (the grammar wraps
replacements around `standalone_word`, not arbitrary content).

### Replacements and Error Coding

Error codes follow the replacement and operate on the replaced word as
a unit:

```chat
*CHI:	rocking+house [: rocking+horse] [*] ?
```

Here `[*]` marks `rocking+house` as containing a phonological/lexical
error; the `[: rocking+horse]` records the intended form. The two
annotations cooperate: the replacement encodes *what was meant*, the
error code classifies *how it deviates*. Implementation:
`scoped_annotations` field on `ReplacedWord`.

## Common Misconceptions

These are bugs we have repeatedly written down then forgotten — recording
them here so future contributors don't reinvent them.

1. **"`[: ...]` lets me put any text I want."** No. Each replacement
   word is validated. `[: C-3PO]` fails E220 in English just as
   `C-3PO` would.
2. **"`[:]` is the right mechanism for ASR sanitization."** Usually
   no. ASR-introduced normalization typically wants `[% ...]` (free-
   form comment) or `[= ...]` (free-form explanation), neither of
   which validates word grammar. Use `[:]` only when you have a
   concrete CHAT-legal intended form.
3. **"`%mor` analyzes the original."** No. `%mor` analyzes the
   replacement. This is the correction's morphology, not the error's.
4. **"`%wor` count must equal `%mor` count."** No. For
   `gonna [: going to]`, `%wor` has 1 entry and `%mor` has 2. They
   align to different sides. The validator's per-domain rule respects
   this.
5. **"`<a b> [: c d]` is a group-level replacement."** No.
   Group-level replacements don't exist. Either replace inside
   (`<a [: c] b [: d]>`) or rephrase the transcription.

## See Also

- [Retraces and Repetitions](./retraces.md) — the orthogonal post-hoc
  correction mechanism.
- [The %mor Tier](./mor-tier.md) — UD-syntax morphosyntactic analysis
  that aligns to the replacement form.
- [Word Syntax](./word-syntax.md) — the word grammar that replacement
  words must satisfy.
- [Dependent Tiers](./dependent-tiers.md) — overview of `%mor`,
  `%wor`, etc., with their alignment relationships.
