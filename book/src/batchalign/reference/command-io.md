# Command inputs and outputs

This table describes the current local CLI. `-o/--out` selects a destination
folder; relative subdirectories are mirrored from the selected inputs' common
root. Discovery accepts individual paths, recursive directories, and file lists.
See [Input selection](../user-guide/cli-reference.md#input-selection).

| Command | Inputs | Output | Without `-o` |
|---|---|---|---|
| `transcribe` | Media; required `--lang` | CHAT | Write `.cha` beside the recording |
| `align` | CHAT with resolvable media | CHAT with word timings | Update source transcript |
| `morphotag` | CHAT | CHAT with `%mor`/`%gra` | Update source transcript |
| `utseg` | CHAT | CHAT with revised utterance boundaries | Update source transcript |
| `translate` | CHAT | CHAT with `%eng` translation tiers | Update source transcript |
| `ai` | CHAT and an instruction | Edited CHAT | Update source transcript |
| `compare` | CHAT with a sibling gold reference | Comparison metrics | Write metrics beside inputs |
| `diarize` | Timed CHAT with resolvable media | CHAT with revised speaker assignments | Update source transcript |
| `convert` | Media and required `--format wav` or `mp3` | Encoded media | Write beside input; same-format conversion uses `.converted` in the name |

`morphotag` strips existing `%mor`/`%gra` from staged inputs by default;
`--keep-existing` preserves them for the engine's already-tagged check.
`convert` rejects pre-existing targets and collisions between selected inputs.

The CLI's per-command collectors and `write_outcome` in
`python/batchalign/cli/_common.py` own these output decisions. Python API callers
receive `Outcome` objects and choose when and where to write them.
