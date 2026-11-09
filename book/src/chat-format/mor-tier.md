# The %mor Tier: Morphological Analysis

**Status:** Reference
**Last updated:** 2026-05-11 20:35 EDT

The `%mor` (morphological) dependent tier provides word-by-word morphosyntactic annotation aligned with the main tier. Each main-tier word receives a morphological code specifying part of speech, lemma, and grammatical features.

## Format Overview

```text
*CHI:	I want cookies .
%mor:	pron|I-Prs-Nom-S1 verb|want-Fin-Ind-Pres-S1 noun|cookie-Plur .
```

Each `%mor` item has the structure **`POS|lemma[-Feature]*`**, where:

- **POS** — part-of-speech category (`noun`, `verb`, `pron`, `det`, `aux`, etc.)
- **`|`** — pipe separator (always present)
- **Lemma** — base form of the word (`cookie`, `be`, `I`). May contain language-specific compound or derivational boundary markers (see [Compound Lemma Boundaries](#compound-lemma-boundaries) below)
- **Features** — zero or more morphological features, each preceded by `-` (`-Plur`, `-Fin-Ind-Pres-S3`)

Items are space-separated and terminate with a punctuation marker (`.`, `?`, `!`, etc.).

## The UD MOR Format

TalkBank's `%mor` tier uses a format inspired by [Universal Dependencies (UD)](https://universaldependencies.org/) but adapted to CHAT conventions. We call this the **UD MOR format** to distinguish it from the older CLAN-era MOR format.

The UD MOR format was introduced via batchalign's Stanza-based morphosyntax pipeline. Stanza produces standard UD analysis (UPOS, lemma, morphological features, dependency relations), and the Rust mapping layer converts this to CHAT `%mor` and `%gra` tiers. The new format has been adopted for all new corpus annotation.

### Structure: Flat POS|lemma\[-Feature]*

Every morphological word is flat — a single POS tag, a single lemma, and a linear chain of features:

```text
POS|lemma[-Feature1][-Feature2][-Feature3]...
```

There are no compounds, prefixes, subcategories, or nested structures in the UD MOR format. The entire morphological analysis of a word is captured by the POS+lemma+features triple.

**Examples:**

| Word | %mor code | POS | Lemma | Features |
|------|-----------|-----|-------|----------|
| dog | `noun\|dog` | noun | dog | (none) |
| dogs | `noun\|dog-Plur` | noun | dog | Plur |
| running | `verb\|run-Part-Pres-S` | verb | run | Part, Pres, S |
| is | `aux\|be-Fin-Ind-Pres-S3` | aux | be | Fin, Ind, Pres, S3 |
| I | `pron\|I-Prs-Nom-S1` | pron | I | Prs, Nom, S1 |
| the | `det\|the-Def-Art` | det | the | Def, Art |

### Multi-Word Tokens (Clitics)

English contractions and similar multi-word tokens (MWTs) are represented using the **tilde (`~`) separator** for post-clitics:

```text
*CHI:	it's red .
%mor:	pron|it~aux|be-Fin-Ind-Pres-S3 adj|red .
```

Here `it's` is a single main-tier word that expands to two morphological words: `pron|it` (main) and `aux|be-Fin-Ind-Pres-S3` (post-clitic). The `~` indicates the two MOR words are fused into one orthographic token.

Each clitic counts as its own **chunk** for `%gra` alignment — `pron|it~aux|be-Fin-Ind-Pres-S3` produces 2 chunks, each needing its own grammatical relation.

### Terminator

The `%mor` tier ends with a terminator that matches the main tier's utterance terminator:

```text
*CHI:	what is that ?
%mor:	pron|what aux|be-Fin-Ind-Pres-S3 det|that ?
```

The terminator (`.`, `?`, `!`, `+...`, etc.) counts as one chunk for `%gra` alignment.

## How It Diverges from UD

The UD MOR format is **UD-inspired but not UD-compliant**. Several deliberate adaptations make it fit CHAT conventions while preserving most UD information. This section catalogs every divergence.

### 1. POS Tags Are Lowercased UPOS

UD uses uppercase UPOS tags (`NOUN`, `VERB`, `PRON`). CHAT uses lowercase (`noun`, `verb`, `pron`). This is a lossless, trivially reversible surface change.

| UD UPOS | CHAT POS |
|---------|----------|
| NOUN | `noun` |
| VERB | `verb` |
| AUX | `aux` |
| PRON | `pron` |
| DET | `det` |
| ADJ | `adj` |
| ADV | `adv` |
| ADP | `adp` |
| PROPN | `propn` |
| INTJ | `intj` |
| CCONJ | `cconj` |
| SCONJ | `sconj` |
| NUM | `num` |
| PART | `part` |
| X | `x` |

### 2. Feature Values Are Flat, Not Key=Value (Currently)

UD represents morphological features as key=value pairs: `Number=Plur`, `Tense=Past`, `Person=3`. The current CHAT convention drops the keys and uses only the values: `-Plur`, `-Past`, `-S3`.

This is the most significant divergence from UD, because:

- **Information loss**: `Plur` could in principle be `Number=Plur` or `Degree=Plur` (though in practice the UD feature value set has no real ambiguities).
- **Collapsed person/number**: UD `Person=3|Number=Sing` becomes `-S3` — a combined code that cannot be mechanically decomposed back to its UD components.
- **Feature ordering**: Features appear in a conventional order determined by the generation pipeline, not in UD's alphabetical order.

**The data model now supports key=value features.** The `MorFeature` type has an optional `key` field — when present, the feature serializes as `Key=Value` (e.g., `-Number=Plur`); when absent, it serializes as just the value (e.g., `-Plur`). This is forward-compatible: existing flat features parse and serialize identically, and if batchalign's mapper begins emitting `Key=Value` features, they flow through the parser and model without any format changes.

### 3. Multi-Value Features: Commas Preserved

UD encodes multi-value features with commas: `PronType=Int,Rel` (the word is *both* interrogative and relative). In CHAT `%mor`, the comma is **preserved within the feature value**:

```text
-Int,Rel
```

This is treated as a single feature value `"Int,Rel"`. The grammar accepts commas within feature values, and the model stores them as-is. No decomposition occurs — the model faithfully records the string that appears in the `%mor` tier.

> **Historical note**: Earlier documentation described a "comma-stripping" convention where `PronType=Int,Rel` became `-IntRel` (concatenated without separator). The current grammar and parser preserve the comma. Existing corpus data using the concatenated form (`-IntRel`) also parses correctly — it's simply treated as the flat value `"IntRel"`.

### 4. Dependency Relations Are Uppercase with Dash Subtypes

The `%gra` tier (not `%mor`, but closely related) uses uppercase relation names with dashes for subtypes, where UD uses lowercase with colons:

| UD | CHAT %gra |
|----|-----------|
| `nsubj` | `NSUBJ` |
| `acl:relcl` | `ACL-RELCL` |
| `obl:tmod` | `OBL-TMOD` |

This is lossless — case and separator are trivially reversible.

### 5. ROOT Head Convention

In UD, the root word has `head=0`. In `%gra`, two conventions coexist:

- **UD convention**: `head=0` (e.g., `3|0|ROOT`) — the standard we now emit
- **Legacy TalkBank convention**: `head=self` (e.g., `3|3|ROOT`) — found in older corpus data

The parser and validator accept both forms. New output uses `head=0`.

### 6. No XPOS, No DEPREL Subtypes in %mor

UD provides both UPOS (universal POS) and XPOS (language-specific POS). CHAT `%mor` uses only UPOS-equivalent tags — there is no XPOS field. Language-specific POS distinctions are not represented.

Similarly, UD's fine-grained dependency relation subtypes (e.g., `nsubj:pass`) appear in `%gra` as `NSUBJ-PASS`, but the `%mor` tier itself contains no dependency information.

### 7. No Morpheme Segmentation

Traditional CHAT MOR formats (CLAN-era) supported morpheme-level segmentation with compound markers (`+`), prefix markers (`#`), and suffix chains (`-SUFFIX&type`). The UD MOR format does not use any of these — each word is analyzed as a flat POS+lemma+features triple.

The grammar still *accepts* some of these legacy markers for backward compatibility with older corpus data, but the canonical UD MOR format does not produce them.

## Compound Lemma Boundaries

Several UD treebanks use special characters *inside* lemmas to mark morphological boundaries. These are meaningful linguistic annotations preserved in the CHAT `%mor` lemma field when possible.

### Known Markers Across Languages

| Language | Marker | Meaning | Example Lemma | In %mor |
|----------|--------|---------|---------------|---------|
| **Estonian** | `=` | Compound boundary | `maja=uks` (house-door) | `noun\|maja=uks` — **preserved** |
| **Basque** | `!` | Derivational boundary | `partxi!se` (share + derivation) | `noun\|partxi!se-Ine` — **preserved** |
| **Finnish** | `#` | Compound boundary | `jää#kaappi` (ice-cabinet) | `noun\|jää_kaappi` — **mangled** (`#` → `_`) |

`=` and `!` pass through the cleaning pipeline because they are not reserved CHAT `%mor` syntax characters. `#` is reserved in traditional CHAT MOR for prefix markers (e.g., `v|#un#do`), so the sanitizer replaces it with `_`.

> **Gotcha: `=` ambiguity with legacy CLAN translation glosses.**
> Legacy CLAN `%mor` tiers use `=` for translation glosses (e.g., `n|perro=dog`), a convention
> predating UD adoption. The parser treats `=` identically in both cases — it is preserved as
> part of the lemma string. This means legacy `n|perro=dog` parses successfully but the
> translation semantics are lost: the model stores `perro=dog` as a single lemma, indistinguishable
> from an Estonian compound like `maja=uks`. Since we cannot reliably disambiguate the two uses
> without language-specific context, legacy translation glosses are silently absorbed into the
> lemma. Files with legacy `=translation` syntax still parse and round-trip correctly, but the
> translation information is not semantically accessible. This affects corpora that predate our
> UD MOR adoption and lack Stanza coverage for their language.

### Multi-Word Expression Lemmas (Stanza `_` Convention)

Stanza uses underscores in lemmas to represent multi-word expressions across many languages: `New_York`, `parce_que` (French), `pick_up` (English), `a_causa_di` (Italian). The current cleaning pipeline strips underscores entirely (`New_York` → `NewYork`), which is a known data quality issue and should be treated as an open data-quality limitation of the current mapper.

### Multi-Value Features (Commas in Feature Values)

UD encodes multi-value features with commas: `PronType=Int,Rel` means a word is *both* interrogative and relative. These commas appear in the CHAT `%mor` feature suffix and are **preserved as-is**:

```text
pron|wat-Int,Rel
```

This is sometimes mistaken for a compound lemma marker, but commas in UD always appear in the **feature column** (CONLLU column 6), never in the **lemma column** (CONLLU column 3). In CHAT `%mor`, they appear after the `-` feature separator, not inside the lemma. The grammar, both parsers, and the data model all accept commas in feature values. See [Section 3: Multi-Value Features](#3-multi-value-features-commas-preserved) above.

### Future Direction

The current handling of compound lemma boundaries is inconsistent across languages. A possible future improvement is a unified Unicode separator character that would normalize all compound/derivational boundary markers (`=`, `!`, `#`, and potentially `_`) into a single convention. This has not been implemented as of 2026-03-02 and requires a design decision on which character to use and whether to preserve the original markers in a structured field.

## Migration from Traditional CHAT MOR

### What Changed

The traditional CHAT MOR format (CLAN-era) used a complex, hierarchically structured notation:

```text
%mor:	pro:sub|I v|want n|cookie-PL .
```

Key differences from the UD MOR format:

| Aspect | Traditional CHAT MOR | UD MOR |
|--------|---------------------|--------|
| **POS tags** | CLAN categories (`pro:sub`, `v`, `n`, `adj`, `adv`) | Lowercased UPOS (`pron`, `verb`, `noun`, `adj`, `adv`) |
| **POS subtypes** | Colon-separated (`pro:sub`, `det:art`, `v:aux`) | Flat (subtypes dropped or encoded differently) |
| **Features** | CLAN suffix system (`-PL`, `-PAST`, `-3S`, `-PRES`) | UD feature values (`-Plur`, `-Past`, `-S3`, `-Pres`) |
| **Compounds** | `+` separator (`n|+n\|black+n\|bird`) | Not used (lemma contains the full form) |
| **Prefixes** | `#` separator (`v|#un#do`) | Not used |
| **Morpheme segmentation** | Full segmentation (`v\|eat&PAST`) | Not used (features are abstract, not morphemic) |
| **Translations** | `=` separator (`n\|perro=dog`) | Not present in base format (separate mechanism) |

### Backward Compatibility

The grammar still accepts many traditional CHAT MOR constructs (colons in POS tags, etc.) because the reference corpus contains files in both formats. The parser produces the same flat `MorWord` regardless — legacy constructs are mapped to the simplified structure during parsing.

### What Stays the Same

Despite the format changes, fundamental CHAT conventions remain:

- Pipe (`|`) separates POS from lemma
- Hyphen (`-`) introduces features
- Tilde (`~`) marks post-clitics
- Space separates items
- Terminator ends the tier
- 1-to-1 alignment with main tier words

## Implementation

For Batchalign's generation of morphology, see the
[Morphosyntax contract](../batchalign/reference/morphosyntax.md).
The parser, data model, and validator are maintained by
[Chatter](../related-tools.md#chatter-and-chat-format-tools).
