# CHAT symbols

This reference summarizes notation used in transcripts. For the complete
conventions, see the [CHAT manual](https://talkbank.org/0info/manuals/CHAT.html).
Parser and symbol-registry development belong to
[Chatter](../related-tools.md#chatter-and-chat-format-tools).

## Symbol Categories

### Terminators

Punctuation that ends an utterance:

| Symbol | Name | Usage |
|--------|------|-------|
| `.` | Period | Declarative |
| `?` | Question | Interrogative |
| `!` | Exclamation | Exclamatory |
| `+...` | Trailing off | Incomplete utterance |
| `+..?` | Trailing-off question | Question trails off |
| `+/.` | Interruption | Speaker interrupted by another |
| `+//.` | Self-interruption | Speaker interrupts self |
| `+/?` | Interrupted question | Question interrupted |
| `+!?` | Broken question | Exclamation-question |
| `+"/.` | Quoted new line | Quotation continues on next line |

### Conversation-analysis notation

Symbols used in conversation analysis notation:

| Symbol | Meaning |
|--------|---------|
| `↑` | Rising pitch |
| `↓` | Falling pitch |
| `→` | Level pitch |
| `↗` | Rise-fall |
| `↘` | Fall-rise |
| `≋` | Creaky voice |
| `∙` | Micropause |

These symbols do not all have the same word-boundary behavior. Pitch arrows
`↑` and `↓` can attach to a word, as in `book↑`; separator symbols such as
`→`, `↗`, and `↘` are separate content items. Do not strip or split all
conversation-analysis symbols using a single punctuation rule.

## Language Codes

CHAT uses ISO 639-3 three-letter language codes in `@Languages` headers and `@s:` word markers:

```chat
@Languages:	eng, fra
*CHI:	I want a croissant@s:fra .
```

Common codes: `eng` (English), `fra` (French), `deu` (German), `spa` (Spanish), `zho` (Mandarin), `jpn` (Japanese).

## Special Markers

### @ Markers (Word-Level)

| Marker | Meaning |
|--------|---------|
| `@s:LANG` | Second language word |
| `@l` | Letter |
| `@c` | Child-invented form |
| `@f` | Family-specific word |
| `@n` | Neologism |
| `@o` | Onomatopoeia |
| `@b` | Babbling |
| `@wp` | Word play |
| `@si` | Signed word |

### & Markers (Events and Fillers)

| Prefix | Meaning |
|--------|---------|
| `&=` | Paralinguistic event (e.g., `&=laughs`) |
| `&-` | Filler (e.g., `&-um`) |
| `&+` | Phonological fragment (e.g., `&+sh`) |
| `&~` | Nonword (e.g., `&~mama`) |
| `&*` | Other speaker's speech event (e.g., `&*MOT:word` — speech attributed to another speaker) |

### Scope Markers

| Marker | Meaning |
|--------|---------|
| `[/]` | Partial retrace — speaker repeats the same words |
| `[//]` | Full retrace — speaker restarts with different words |
| `[///]` | Multiple retracing — multiple false starts |
| `[/-]` | Reformulation — speaker rephrases with different structure |
| `[*]` | Error |
| `[?]` | Best guess |
| `[>]` | Overlap follows |
| `[<]` | Overlap precedes |
| `[= text]` | Explanation |
| `[: text]` | Replacement |
