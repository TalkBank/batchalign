# Align a transcript to its recording

Use `align` after checking the transcript's words. It adds word-level timing
information, including a `%wor` tier.

1. Put the CHAT transcript and its recording together. Check that `@Media:`
   names the recording and `@Languages:` identifies the transcript language.
2. Run:

   ```bash
   batchalign align corpus/ -o aligned/
   ```

3. Wait for the final summary. Open the output transcript and check playback
   against the recording, especially long turns and overlapping speech.

The default forced-alignment engine is `wav2vec`. When utterance timings are
missing, the default timing-recovery engine is Rev.AI; configure its credentials
if prompted. Already-timed utterances can avoid that recovery step.

## Use local timing recovery

```bash
batchalign align corpus/ -o aligned/ --utr-engine whisper
```

To use Whisper for forced alignment as well:

```bash
batchalign align corpus/ -o aligned/ --engine whisper --utr-engine whisper
```

Use `--utr-engine none` only when the transcript already has the timings required
for forced alignment. Keep different transcript languages in separate alignment
invocations: the CLI chooses a backend language from the selected CHAT inputs.

Without `-o`, source transcripts are updated in place. For model and device
options, see [CLI reference](../cli-reference.md#align).
