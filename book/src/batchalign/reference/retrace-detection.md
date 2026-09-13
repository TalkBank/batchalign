# Automatic retrace detection

The ASR cleanup pass can mark earlier copies of an immediately repeated word
sequence as retraces. Matching is case-insensitive; the word spelling is retained.
It is a local repetition heuristic, not a detector of every conversational repair.

Fillers participate in sequence matching but are not themselves changed into
retrace words. Repeating a filler alone therefore does not create a retrace mark.
The minimum sequence length is two for the `yue` and `zho` language keys and one
for other keys in the current implementation.

The pass sets typed word kinds. The CHAT builder uses those kinds to construct
retrace annotations rather than embedding bracket syntax in word text. Review
these automatic decisions against the recording.

Source: `crates/batchalign/batchalign-core/src/asr/cleanup.rs::apply_retrace_detection`.
For CHAT notation, see [Retraces and repetitions](../../chat-format/retraces.md).
