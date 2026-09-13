# Review generated transcripts and timings

1. Keep the original transcript or recording and write processing output to a
   separate folder with `-o`.
2. Read the command's final summary and inspect failed or skipped files before
   relying on the output set.
3. For transcription, listen to the recording and correct words, speaker labels,
   and utterance boundaries. ASR output is marked as unchecked.
4. For alignment, check playback at utterance and word boundaries, especially
   where speakers overlap or the recording is noisy.
5. For morphology, inspect `%mor` and `%gra` against the intended words and
   language. If retokenization was enabled, review main-tier changes too.

Older files may contain `%xalign` decision notes or `%xrev` review markers from
other processing versions. Their presence does not prove that the current run
created them, and their absence does not prove an output is correct. The current
CLI does not expose the old `--review-level` controls.

Use [provenance comments](provenance.md) to identify a producing build and task.
A file modification timestamp alone cannot establish which utterances were
edited or whether a previous review remains valid.
