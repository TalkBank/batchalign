# Language selection

Language selection is command-specific. A valid language identifier does not by
itself establish that a selected model supports that language.

| Entry point | Language source |
|---|---|
| `transcribe` | Required `--lang`, validated as ISO 639-3 |
| `morphotag` | CHAT `@Languages:` and applicable utterance-level language markers |
| `align` | Language inferred from selected CHAT input for backend construction |
| `utseg` | Backend `--language` option, default `en` |
| `translate` | `--target` selects output language, default `eng` |

For transcription, examples include `eng` (English), `spa` (Spanish), `cmn`
(Mandarin), and `yue` (Cantonese). `python/batchalign/lang.py::LanguageCode`
normalizes whitespace and case and resolves three-letter identifiers using
`pycountry`; backends choose the vendor-specific form they require.

## Morphosyntax language routing

The Rust runner derives a language specification from CHAT. The Stanza backend
resolves that specification to model language codes, groups requests by language
configuration, and constructs a single-language or multilingual pipeline as
needed. Its process-wide LRU retains at most two language/mode configurations.
The CLI groups files by language headers to reduce model switching.

The current CLI does not expose the former `--skipmultilang`, `--no-l2-morphotag`,
or `--no-pos-hints` switches. Older language experiments that use those switches
must not be used as current operational instructions or accuracy guarantees.

For the implemented token and language workarounds, inspect
`python/batchalign/backends/morphosyntax/ud/lang.py`, its language submodules,
and the core morphology runner. For command syntax, see [CLI reference](../user-guide/cli-reference.md).
