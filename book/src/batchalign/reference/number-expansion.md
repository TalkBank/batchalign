# Number expansion in ASR output

Speech recognizers can return digits where a CHAT transcript needs spoken words.
The Rust ASR cleanup pipeline expands supported numeric forms before CHAT
assembly. Expansion is language-dependent: it is not a single English rule
applied to every recording.

The current implementation is in core `asr/num2text.rs`, `asr/num2chinese.rs`,
`asr/ordinal_year_eng.rs`, and `asr/expand.rs`. Language data is in
`asr/data/num2lang.json`. These sources determine which cardinal, ordinal,
year, percent, and other forms are handled. Unsupported forms can survive
normalization, so inspect output rather than assuming that every digit was expanded.

Expansion can turn one recognizer token into several words. The ASR preparation
pipeline also handles word splitting and timing propagation; the spelling and
number of final CHAT words need not match the recognizer's raw token sequence.
For the surrounding stages, see [ASR processing](../architecture/asr-token-pipeline.md).
