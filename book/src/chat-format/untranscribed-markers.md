# Untranscribed Markers: `xxx`, `yyy`, `www`

**Status:** Reference
**Last updated:** 2026-05-11 23:21 EDT

CHAT reserves three short word-level markers for material the human
transcriber cannot or chose not to render as words on the main tier.
Each one has a specific meaning. Tools that emit CHAT — including ASR
pipelines, format converters, and editor heuristics — must respect
those meanings, because every downstream consumer (researchers,
validators, and aggregate-statistics tools like CLAN's `freq`,
`kideval`, `mlu`) reads them at face value.

| Marker | Meaning | Emitter |
|---|---|---|
| `xxx` | Transcriber listened to the audio and **could not make out** what was said. The speech is unintelligible to the human ear at this point. | Human transcriber only. |
| `yyy` | Transcriber heard a discrete utterance but could not write it as ordinary CHAT words. Used when the surface form resists orthography (mumbled, slurred, foreign with no equivalent). The phonetic content typically appears on the `%pho` tier. | Human transcriber only. |
| `www` | Transcriber chose **not to transcribe** this stretch — usually for privacy, off-topic content, or because the segment is irrelevant to the corpus's purpose. | Human transcriber only. |

The shared property: each marker is the human transcriber telling
later readers something specific about *their experience listening to
the audio*. None of them mean "tooling could not process this token".

## Why this matters

When a researcher loads a CHAT corpus and counts `xxx` occurrences, the
result is a *measure of human listening difficulty*: it tells them how
much of the audio resisted human transcription. That number feeds into
methodology decisions ("can we get reliable MLU from this corpus?",
"what's the noise floor on this child's speech?", "should we re-record
in a quieter environment next time?"). It is a load-bearing signal in
language-development research.

If an ASR pipeline emits `xxx` whenever it can't sanitize a token —
for example, substituting `xxx` for any word that fails CHAT
validation under a strict language profile — every `xxx` count in the
corpus becomes a meaningless mixture of "human couldn't tell" and
"pipeline gave up". Researchers then reading those counts are silently
misled. The signal is destroyed for the entire history of that
corpus, because the corruption is indistinguishable from real
unintelligibility once committed.

The same reasoning applies to `yyy` and `www`. A converter or
post-processor that emits any of these three markers because *the
tooling* couldn't handle a token is committing semantic vandalism
against the whole field.

## Rules for tooling

1. **Never emit `xxx`, `yyy`, or `www` from a tool to mean "could not
   process".** These markers are reserved for human transcriber
   judgment.
2. **When a token cannot be validated as legal CHAT under the
   declared language**, prefer one of:
   - Pass the token through verbatim and let the CHAT validator
     (or CLAN's `check`) flag it for human review. The transcriber
     listens, decides, and corrects.
   - Fail loud — abort the file rather than emit corrupted output.
   - Apply only purely orthographic, semantically null repairs
     (e.g., stripping a stray boundary quote mark from `"My`). These
     are safe because no information is lost.
3. **Never sanitize a token by replacing it with one of the three
   markers.** That is exactly the corrupting behavior this document
   prohibits.
4. **Never delete a token to "fix" a validation failure.** Deletion
   loses data without any flag.

## Review ASR output

An ASR error is not evidence that the original speech was unintelligible.
Listen to the recording before introducing `xxx`, `yyy`, or `www`.
See [Transcribe a recording](../batchalign/user-guide/commands/transcribe.md)
and [ASR output processing](../batchalign/architecture/asr-token-pipeline.md)
for Batchalign's current workflow.
