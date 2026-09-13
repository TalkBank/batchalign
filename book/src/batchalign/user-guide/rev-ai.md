# Configure Rev.AI transcription

Rev.AI is the default speech-recognition backend for `transcribe` and the default
utterance-timing recovery backend for `align`.

## Set up your key

Run an interactive transcription command:

```bash
batchalign transcribe recordings/ -o transcripts/ --lang eng --engine rev
```

When prompted, enter your Rev.AI API key. Interactive configuration stores the
key in `~/.batchalign.ini`, under `[asr]` as `engine.rev.key`.

For automation, supply `BATCHALIGN_REV_KEY` through your environment or secret
manager. Quiet mode suppresses interactive credential prompts. The current CLI
has no `setup` subcommand.

## Use the configured account

```bash
batchalign transcribe recordings/ -o transcripts/ --lang eng --engine rev
batchalign align corpus/ -o aligned/ --utr-engine rev
```

These operations can upload audio to Rev.AI. Use an account and recordings
appropriate for your organization's workflow. To select a local transcription
backend, see [Transcribe a recording](commands/transcribe.md#use-a-local-speech-model).

The integration is implemented in the Python backends and configuration module,
not a separate Rust server path.
