# From recognition output to CHAT

The transcription runner sends prepared audio, a language hint, and task options
to the selected ASR backend. The returned segments and words are converted to
Rust ASR structures for cleanup and CHAT assembly.

The core `asr/` modules handle compound merging, timed-word extraction, splitting
multiword recognizer tokens, numeric forms, orthographic cleanup, and construction
of CHAT utterances and headers. Some cleanup is language-specific. Backends also
normalize their own vendor outputs before returning the typed ASR result.

This means a backend token and a final CHAT word are not interchangeable. A single
recognizer token can be split, a numeric token can expand into several words,
and punctuation can be represented as a CHAT terminator rather than word text.
Timing must remain attached to the transformed content through these steps.

The recipe can run an utterance-segmentation backend after ASR and a speaker
backend afterward. It does not automatically append forced alignment or morphology.
Generated CHAT includes the unchecked-ASR comment, and successful pipeline outputs
receive task provenance.

Source: core `taskrunners/asr.rs`, `asr/prepare.rs`, `asr/cleanup.rs`,
`asr/expand.rs`, `asr/chat/`, and `python/batchalign/recipes.py`.
