# Python CHAT documents

`batchalign.chat` exposes four Rust-backed types: `CHATFile`, `Speaker`,
`Utterance`, and `Media`. Python imports these types from `batchalign._core`;
parsing, validation, storage, and edits happen in Rust using the TalkBank model.
`CHATFile`, `Media`, and `Utterance` are also available directly from `batchalign`.
Import the CHAT `Speaker` from `batchalign.chat`; `batchalign.Speaker` remains
the diarization backend base class.

## Create a document

```python
from batchalign.chat import CHATFile, Media, Speaker, Utterance

child = Speaker(
    "CHI",
    language="eng",
    corpus="example",
    role="Target_Child",
    name="Sam",
)
chat = CHATFile.new()
chat.media = Media("recording", media_type="audio")
chat.utterances.append(
    Utterance(child, "I want a cookie .", timing=(1000, 2500))
)

print(len(chat))  # 1: the number of utterances
print(chat.stringify())
```

`Speaker(code, *, language, corpus, role="Participant", name=None)` requires
explicit language and corpus information. `language` accepts a language-code
string or a list of codes for a multilingual speaker. Codes use CHAT's ISO 639-3
form, such as `eng`, `fra`, and `nld`. Speaker values are immutable; replace an
utterance's speaker to change its participant metadata.

`Utterance(speaker, text, *, timing=None)` takes a `Speaker` and CHAT main-tier
content, including its terminator. It does not take the `*CHI:` prefix. Timing
is either `None` or a pair of nonnegative integer milliseconds with start less
than end. Put timing in `timing`, rather than embedding a bullet in `text`.

An empty `CHATFile.new()` is an editable draft. Participant headers appear when
utterances are added. No placeholder speaker, corpus, or language is invented.

## Read and write

```python
with open("input.cha", encoding="utf-8") as fd:
    chat = CHATFile.read(fd)

copy = CHATFile.parse(chat.stringify())
copy_from_lines = CHATFile.parse(chat.stringify().splitlines())

with open("output.cha", "w", encoding="utf-8") as fd:
    chat.write(fd)

assert str(chat) == chat.stringify()
```

`parse` accepts a string or a list of strings. List entries may include their
line endings. `read` and `write` take open text streams and leave them open.
They operate from the stream's current position. Binary streams and paths are
not accepted in place of text streams.

Serialization uses canonical CHAT formatting. Parsed dependent tiers,
participant ID fields (including age, sex, group, education, and custom fields),
and unrelated headers such as dates and comments are preserved. Comments retain
their position relative to existing utterances.

## Navigate and edit utterances

```python
utterance = chat.utterances[0]
print(utterance.speaker.code)
print(utterance.words)       # read-only tuple of word-timing units
print(utterance.timing)      # (start_ms, end_ms), or None
print(utterance.tiers["pho"])

utterance.timing = (1200, 2700)
utterance.tiers["com"] = "reviewed by the transcriber"
```

`utterance.text`, `.speaker`, and `.timing` are editable. `.words` is a read-only
tuple obtained through the model's word-timing traversal; it handles CHAT groups
and annotations rather than splitting text on spaces. Edit `.text` to change
the main tier.

`.tiers` is a live mapping from labels without `%` (for example `pho`, `mor`,
`gra`, and `com`) to CHAT tier content strings. Read, assign, delete, iterate,
and use `len` on it. Assigning an existing label replaces that tier in place.
Edits validate all dependent tiers together; for example, `%gra` requires
compatible `%mor` content. An invalid local edit raises before changing the
utterance. Editing text can fail if existing dependent tiers no longer align.

`chat.utterances` supports iteration, integer indexing, read slices, `append`,
`insert`, integer replacement and deletion, `pop`, and `clear`. Negative indices
follow Python conventions. Slices return lists; slice assignment is not supported.

The collection stores live utterance objects. Appending an object and then
editing that object updates the document. Inserting or removing other utterances
does not invalidate existing handles. A removed utterance remains usable but
no longer contributes to that document. Appending the same object to multiple
documents shares its edits. Iteration takes a snapshot of the collection's
references, while the referenced utterances remain live.

## Derived participant metadata

```python
print(chat.speakers)                  # tuple of Speaker values
print(chat.languages)                 # tuple of distinct language codes
print(chat.corpora)                   # tuple of distinct corpus names
print(chat.utterances[0].speaker.languages)
```

These document properties are derived from referenced speakers in first-use
order. Languages also include resolved utterance and word-level language choices.
If regenerating the language order changes the file default, serialization adds
an explicit language precode where needed to preserve an utterance's meaning.
These properties and their contents are read-only: assignment or mutation raises.
`@Participants`, `@ID`, and `@Languages` are generated from those speakers.
Silent participants are omitted from this Python API and its serialized output.
Two utterances using the same speaker code must agree on participant metadata.
Collection insertion and replacement reject conflicting speaker definitions.

## Media and validation

`Media(filename, *, media_type="audio", status=None)` represents `@Media`.
`filename` is a CHAT media basename without an extension. `media_type` accepts
`audio`, `video`, or `missing`; `status` accepts `None`, `missing`, `unlinked`,
or `notrans`. Media values are immutable.

```python
chat.media = Media("recording", media_type="audio", status="unlinked")
print(chat.media.filename)
chat.media = None  # remove @Media
```

There is no generic header type or editable header mapping. Participant headers
are derived; media has its own typed property. Other parsed headers are retained.

Wrong input types raise `TypeError`. Invalid CHAT or metadata values raise
`ValueError` with model diagnostics; negative unsigned timestamps raise
`OverflowError`. Missing tier labels raise `KeyError`, and out-of-range utterance
indices raise `IndexError`.

Constructors and utterance edits validate local content and tier alignment.
`stringify`, `str`, and `write` also validate document-wide constraints, including
speaker consistency and media linkage. During editing, setting a media declaration
before adding timed utterances is allowed; serializing the resulting document
still requires valid CHAT. Timed transcripts require media; untimed transcripts
declaring media should use an appropriate status such as `unlinked`.

This API is separate from pipeline inputs. To run a file through a recipe, use
the input constructors described in the [Python API reference](../user-guide/python-api.md).
