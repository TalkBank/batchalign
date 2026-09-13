# Process Cantonese recordings and transcripts

For a local Cantonese ASR backend, select `funaudio` and the required language
code `yue`:

```bash
batchalign transcribe recordings/ -o transcripts/ --lang yue --engine funaudio
```

Cloud choices include `tencent` and `aliyun`; their credentials and model options
are owned by the corresponding Python backend. Use `--engine`, not the retired
JSON engine-override flag. Review the draft words before subsequent analysis.

For morphology, check that the CHAT header contains `@Languages: yue`, then run:

```bash
batchalign morphotag transcripts/ -o tagged/ --retokenize
```

Retokenization allows word boundaries to change, so inspect the main tiers and
analysis tiers in the output. For alignment, follow [Align a transcript](commands/align.md);
model coverage must match the recording and transcript language.
