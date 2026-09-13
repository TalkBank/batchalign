# Transcribe a recording

Use `transcribe` to produce a draft CHAT transcript from a recording. You will
need to listen to the recording and correct the draft afterward.

1. Place the recording in a folder you can find, such as `recordings`.
2. Run the following for English speech:

   ```bash
   batchalign transcribe recordings/ -o transcripts/ --lang eng
   ```

3. The default engine is Rev.AI. If you have not configured it, follow the
   credential prompt. Rev.AI processes uploaded audio through your account.
   See [Configure Rev.AI](../rev-ai.md).
4. Wait for the final summary. Open the `.cha` file in `transcripts` and review
   the words, speaker labels, and utterance boundaries against the recording.
   Generated transcripts include an `Unchecked output of ASR model` comment.

Use the appropriate three-letter language code, such as `spa` for Spanish or
`cmn` for Mandarin, instead of `eng`. `--lang` is required.
Without `-o`, the transcript is written beside the source recording.

## Use a local speech model

To use the Hugging Face Whisper backend:

```bash
batchalign transcribe recordings/ -o transcripts/ --lang eng --engine whisper
```

The first run downloads the selected model. `--engine openai` selects the local
`openai-whisper` package; it does not mean the hosted OpenAI transcription API.
See [CLI reference](../cli-reference.md#transcribe) for the engine choices.

## Request separate speaker diarization

```bash
batchalign transcribe recordings/ -o transcripts/ --lang eng --diarize --num-speakers 2
```

This adds a separate speaker-assignment stage using the selected diarization
backend. Provider speaker labels may already be present without this option.

## Add word timings or refine alignment

Use `--wor` to retain word-level timing output from transcription. For forced
alignment of a corrected transcript, run [align](align.md) afterward. Transcription
does not automatically run forced alignment or morphosyntactic analysis.
