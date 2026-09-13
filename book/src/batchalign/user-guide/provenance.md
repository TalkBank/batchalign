# Processing Provenance

**Status:** Current
**Last updated:** 2026-05-11 11:40 EDT

## What is provenance?

Every time batchalign3 processes a CHAT file, it records what it did in a
`@Comment` header. This creates a machine-readable processing history
inside the file itself.

## Format

Batchalign3 provenance comments use a structured format inside square
brackets:

```chat
@Comment:	[ba3 morphotag | engine=stanza-1.11.1 ; lang=eng | 2026-03-29T18:30:00-04:00]
```

The format is: `[ba3 <command> | <key>=<value> ; ... | <timestamp>]`

- **`ba3`** — identifies this as a batchalign3 provenance comment
- **command** — which operation was performed
- **key=value pairs** — engine versions and options that affect output
- **timestamp** — ISO 8601 with timezone, when processing occurred

## Example: Multiple Commands

When you run morphotag, then align on the same file, both comments
accumulate:

```chat
@UTF8
@Begin
@Languages:	eng
@Participants:	CHI Target_Child
@ID:	eng|test|CHI|2;0.||||Target_Child|||
@Comment:	[ba3 morphotag | engine=stanza-1.11.1 ; lang=eng | 2026-03-29T18:30:00-04:00]
@Comment:	[ba3 align | fa=whisper-fa-large-v2 ; lang=eng | 2026-03-29T19:15:00-04:00]
*CHI:	the dog is running . 0_4500
%mor:	det|the-Def-Art noun|dog aux|be-Fin-Ind-Pres-S3 verb|run-Part-Pres-S .
%gra:	1|2|DET 2|4|NSUBJ 3|4|AUX 4|0|ROOT 5|4|PUNCT
@End
```

## Re-running a command

If you re-run morphotag on a file that already has a morphotag provenance
comment, the old comment is **replaced** — not duplicated. Comments from
other commands (align, transcribe, etc.) are preserved.

## What each command records

### morphotag

```text
[ba3 morphotag | engine=stanza-1.11.1 ; lang=eng | ...]
```

| Key | Meaning |
|-----|---------|
| `engine` | Stanza version used for POS/lemma/depparse |
| `lang` | Language code |
| `retokenize` | Present if CJK retokenization was applied |
| `incremental` | Present if `--before` incremental mode was used |

### align

```text
[ba3 align | fa=whisper-fa-large-v2 ; lang=eng ; utr=rev | ...]
```

| Key | Meaning |
|-----|---------|
| `fa` | Forced alignment engine and version |
| `lang` | Language code |
| `utr` | UTR engine (if utterance timing recovery was used) |
| `wor` | Present if %wor tier was written |
| `incremental` | Present if `--before` incremental mode was used |

### transcribe

```text
[ba3 transcribe | asr=rev ; lang=eng | ...]
```

| Key | Meaning |
|-----|---------|
| `asr` | ASR engine (rev, whisper, tencent, aliyun, funaudio) |
| `lang` | Language code |
| `diarize` | Present if speaker diarization was enabled |
| `wor` | Present if %wor tier was written |

### utseg

```text
[ba3 utseg | engine=stanza-1.11.1 ; lang=eng | ...]
```

### translate

```text
[ba3 translate | engine=googletrans-v1 ; lang=spa | ...]
```

### coref

```text
[ba3 coref | engine=stanza ; lang=eng | ...]
```

## Parsing provenance programmatically

The `[ba3 ...]` prefix makes provenance comments easy to extract:

```bash
# Find all provenance comments in a file
grep '\[ba3 ' file.cha

# Find all files that were morphotagged
grep -rl '\[ba3 morphotag' corpus/
```

In Python:

```python
import re

PROVENANCE_RE = re.compile(
    r'^\[ba3 (\w+) \| (.*?) \| (\S+)\]$'
)

with open('file.cha') as f:
    for line in f:
        if line.startswith('@Comment:') and '[ba3 ' in line:
            content = line.split('\t', 1)[1].strip()
            m = PROVENANCE_RE.match(content)
            if m:
                command = m.group(1)     # "morphotag"
                fields = m.group(2)      # "engine=stanza-1.11.1 ; lang=eng"
                timestamp = m.group(3)   # "2026-03-29T18:30:00-04:00"
```

## What is NOT recorded

Runtime options that don't affect output are omitted:
- `--parallel` (concurrency)
- `--timeout` (inference timeout)
- `--batch-window` (batching)
- `--server` (where processing happened)
- `--verbose` (logging)
- `--tui` / `--no-tui` (display)

These are operational, not semantic.
