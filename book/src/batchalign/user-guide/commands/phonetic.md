# Add acoustic phonetic transcription

Use `phonetic` to add observed IPA to the `%pho` tier of a timed CHAT transcript.
Place matching audio beside the transcript, or pass a separate media directory
with `--media`. Utterances need timing bullets; existing phonetic tiers are
preserved.

```bash
batchalign phonetic transcripts/ -o phonetic/
```

The default engine is PhoneticXeus. Adjacent utterances share approximately
20-second inference windows. Reference pronunciations help assign the recognized
phones to transcript words; they do not replace observed speech with a canonical
pronunciation. Unresolved words receive `…`.

## Pasketti for English speech

```bash
batchalign phonetic transcripts/ -o phonetic/ --engine pasketti
```

This selects
[pasketti-phonetic](https://huggingface.co/drivendata/pasketti-phonetic), an
English child-speech WavLM CTC model. It processes utterances separately,
resamples audio to 16 kHz, and runs in full precision. Install
`batchalign[phonetic]` for local inference dependencies. Model weights download
on first use.

This is separate from `transcribe --engine pasketti`, which selects
[pasketti-word](https://huggingface.co/drivendata/pasketti-word) to produce a
word transcript. Review both models' output against the recording.

## Pronunciation overrides and memory

```bash
batchalign phonetic transcripts/ -o phonetic/ --pronunciations words.csv --force-cpu --batch-size 1
```

The optional UTF-8 CSV has a `word,ipa` header, followed by overrides such as
`wug,wʌɡ`. Overrides affect the reference used for phone ownership, not the
recognized phones. The default model batch size is 1 on CPU and 2 on CUDA.
Reduce `--batch-size` if model batches exceed available memory.

See [CLI reference](../cli-reference.md#phonetic) for options.
