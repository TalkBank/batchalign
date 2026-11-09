# Phon Tiers (%xmodsyl, %xphosyl, %xphoaln)

**Status:** Reference
**Last updated:** 2026-05-11 22:05 EDT

The Phon extension tiers provide syllable-level phonological annotation and
segmental alignment between target and actual IPA transcription. They are
produced by the [Phon](https://www.phon.ca/phon-manual/getting_started.html)
application and exported to CHAT via
[PhonTalk](https://github.com/phon-ca/phontalk).

> **Note on the `x` prefix:** These tiers currently use the `%x` prefix (`%xmodsyl`, `%xphosyl`, `%xphoaln`) to indicate they are user-defined extension tiers, following the Phon project's convention. When these tiers are officially adopted into the CHAT standard, the `x` prefix will be dropped.

## Background

Phon is a software program for phonological analysis of child language,
second language acquisition, and speech disorders. It stores phonological
data in its own XML session format with structured IPA transcription,
syllabification, and phone-level alignment. When Phon data is exported to
CHAT, three extension tiers carry this phonological annotation:

- **%xmodsyl** — syllabified version of `%mod` (target/model IPA)
- **%xphosyl** — syllabified version of `%pho` (actual IPA)
- **%xphoaln** — phone-by-phone alignment between target and actual IPA

These tiers are derived views of the parent IPA tiers. The syllabification
tiers store the same phoneme sequence as `%mod`/`%pho` but with syllable
structure annotations applied. There is no independent alignment — the
syllabification is a reannotation of the same phone sequence.

## Tier Format

### %xmodsyl / %xphosyl — Syllabified Phonology

Each phoneme is annotated with a syllable constituent position code:

| Code | Meaning |
|------|---------|
| `N` | Nucleus (vowel center) |
| `O` | Onset (syllable-initial consonant) |
| `C` | Coda (syllable-final consonant) |
| `D` | Left appendix |
| `E` | Ambisyllabic / right appendix |
| `R` | Rime / rhotic |

Format: `phone:Position` pairs concatenated within each syllable, with `.`
separating syllables within a word and spaces separating words.

```chat
*CHI:	I want three cookies .
%mod:	aɪ wɑnt θri kʊkiz .
%xmodsyl:	a:Dɪ:D w:Oɑ:Nn:Ct:C θ:Oɹ:Oi:N k:Oʊ:Nk:Oɪ:Nz:C .
%pho:	aɪ wɑn fwi kʊkiz .
%xphosyl:	a:Dɪ:D w:Oɑ:Nn:C f:Ow:Oi:N k:Oʊ:Nk:Oɪ:Nz:C .
```

Pauses appear as `(.)` in the syllabification tiers, matching their
representation in `%mod`/`%pho`:

```chat
%pho:	aɪ (.) wɑnt .
%xphosyl:	a:Dɪ:D (.) w:Oɑ:Nn:Ct:C .
```

### %xphoaln — Phone Alignment

Shows phoneme-by-phoneme correspondence between target (`%mod`) and actual
(`%pho`) IPA using `target↔actual` notation. Multiple pairs within a word
are comma-separated. `∅` marks deletions (target phone with no actual
counterpart) or insertions (actual phone with no target counterpart).

```chat
*CHI:	the best .
%mod:	ðə bɛst .
%pho:	ðə bɛs .
%xphoaln:	ð↔ð,ə↔ə b↔b,ɛ↔ɛ,s↔s,t↔∅ .
```

The `%xphoaln` tier aligns positionally with both `%mod` and `%pho` — word N
in `%xphoaln` corresponds to word N in both parent tiers.

## Alignment Semantics

Because the syllabification tiers are derived views, word counts must match:

- `%xmodsyl` word count = `%mod` word count
- `%xphosyl` word count = `%pho` word count
- `%xphoaln` word count = `%mod` word count = `%pho` word count

Mismatches are flagged as errors E725–E728. See
[Chatter alignment documentation](../related-tools.md#chatter-and-chat-format-tools)
for implementation details.

## Implementation ownership

Phonological analysis belongs to [Phon](https://www.phon.ca/).
CHAT parsing and tier-alignment validation belong to
[Chatter](../related-tools.md#chatter-and-chat-format-tools).
Batchalign can add observed IPA with the [phonetic command](../batchalign/user-guide/commands/phonetic.md).

## Phon XML Source Format

In Phon's native XML format, phonological data is stored as structured
elements:

```xml
<ipaTarget>
  <pho>
    <pw>
      <ph scType="onset"><base>θ</base></ph>
      <ph scType="nucleus"><base>ɹ</base></ph>
      <ph scType="nucleus"><base>i</base></ph>
    </pw>
  </pho>
</ipaTarget>
```

Each `<pw>` (phonological word) element contains `<ph>` elements with
syllable constituent types (`scType`). Pauses appear as `<pause>` elements
at the same level as `<pw>` inside `<pho>`.

The `<alignment>` element provides phone-level mappings between target and
actual using index-based `<pm>` (phone map) entries.

## Data Quality Notes

A small percentage of Phon corpus XML records have an orthography↔IPA
word-count mismatch — i.e. the number of `<pw>` (phonological word)
elements in `<ipaTarget>` / `<ipaActual>` differs from the number of `<w>`
elements in `<orthography>`. This is expected in child phonology data:
children may produce extra syllables, partial words, or over-productions
relative to the target.

For current counts on the data repos in `~/0tb/data/`, run:

```bash
python3 scripts/analysis/scan_phon_mismatches.py ~/0tb/data
```

It reports total XML files scanned, files with at least one mismatched
record, and total mismatched records across the corpus.

The PhonTalk CHAT export handles this discrepancy inconsistently:

1. `%mod`/`%pho` are written through a `OneToOne` alignment path that maps
   IPA words to orthography words — extras are silently dropped
2. `%xmodsyl`/`%xphosyl`/`%xphoaln` are written directly from the raw
   `IPATranscript` — all IPA words are included

This produces CHAT files where `%xmodsyl` may have more words than `%mod`,
triggering E725–E728 validation errors.

This is being investigated in collaboration with the Phon team.
