# Number expansion in ASR output

The Rust ASR pipeline recognizes numeric expressions and expands them before
building CHAT. All ASR backends use this path. It does not invoke Python
`num2words` or depend on morphosyntactic analysis.

## Recognition and rendering

| Source | Responsibility |
|--------|----------------|
| `asr/data/number_rules.json` | Ordered regular expressions, named captures, language selection, and punctuation protection |
| `asr/num2text/mod.rs` | Compile rules once, recognize expressions, dispatch captures, and distinguish unsupported expressions from ordinary text |
| `asr/num2text/eng.rs` | English ordinal and decade rendering |
| `asr/num2text/por.rs` | Portuguese ordinal rendering with gender and plural agreement |
| `asr/num2text/table.rs` and `asr/data/num2lang.json` | Existing cardinal lookup tables for 46 languages and integer decomposition |
| `asr/num2text/cjk.rs` and `asr/num2chinese.rs` | Existing CJK conversion and script selection |
| `asr/num2text/common.rs` | Shared cardinal, currency, numeric-group, and hyphenated-compound handlers; percentage vocabulary |
| `asr/prepare.rs` and `asr/expand.rs` | Tokenization, protected abbreviation spans, and timing propagation |

Language rules are tried in their JSON array order, then common rules. The first
match selects the handler; unsupported rendering does not fall through to a
less specific interpretation. Patterns match entire tokens and provide named
captures such as `value`, `gender`, or `symbol`. Languages without a special
renderer use their cardinal table when available.

Rules marked `protect_punctuation` also participate in ASR tokenization. For
example, the Portuguese ordinal in `54.ª.` consumes its abbreviation period,
but leaves the final period as a sentence terminator. Protection requires a
complete expression boundary; it does not match prefixes of longer words.

## Supported forms and limits

- Cardinal tables retain their existing exact entries and decomposition behavior.
  This refactor does not add grammatical context to cardinal generation.
- English ordinals and decades retain the existing Rust implementation.
- Portuguese ordinals accept digits followed by `º` or `ª`, an optional
  abbreviation period, and optional plural `s`: `54ª`, `54.ª`, `54ºs`.
  Values 1–1000 are supported. For example, `54ª` becomes
  `quinquagésima quarta`; `54.º` becomes `quinquagésimo quarto`.
- Degree `°`, plain letters `a`/`o`, and arbitrary embedded digits are not
  interpreted as Portuguese ordinal markers.
- Currency expansion retains the previous currency vocabulary, including English
  currency labels for non-English languages. Percentages retain their separate
  preparation-stage handling.

The Portuguese forms follow the ordinal composition described in
[Ciberdúvidas](https://ciberduvidas.iscte-iul.pt/consultorio/perguntas/ordinais-diversos/13396).
Expansion reflects the recognizer's written interpretation; it cannot establish
which words the speaker actually said.

## Results and timing

Recognition and rendering distinguish ordinary text, a successful expansion,
and a recognized but unsupported expression. Unsupported expressions retain
their source text and produce a debug diagnostic. The normal CHAT validation
still applies and can reject remaining digits with E220.

An expansion can contain several words. The ASR pipeline retains the original
token's overall time span and apportions internal boundaries by character count;
these are approximate boundaries for subsequent forced alignment to refine.
It retains speaker information outside the language renderer.

The regression suite checks frozen outputs from the previous converter across
all table languages and CJK/fallback paths, every applicable cardinal-table entry,
and Portuguese ordinal recognition, CHAT legality, punctuation, and timings.
For surrounding stages, see [ASR processing](../architecture/asr-token-pipeline.md).
