# Media conversion

`batchalign convert` accepts media paths and requires `--format wav` or `mp3`.
The default recipe selects the native Rust conversion backend and bypasses the
shared result cache. The output is an encoded media file, not a cached temporary
artifact managed by an old server media-cache directory.

```bash
batchalign convert recordings/ --format wav -o wav-recordings/
```

The CLI rejects existing output targets, source-overwriting targets, and two
inputs that would map to the same output. If a same-format conversion is written
beside the input, the name includes `.converted` to keep it distinct.

Input discovery recognizes common audio/video suffixes, but recognition alone
does not establish that every codec/container can be decoded. Consult the
conversion backend and test a representative file.

Source: `python/batchalign/cli/convert.py`, `recipes.py::convert`,
`crates/batchalign/batchalign-core/src/taskrunners/convert.rs`, and the core/engine
native conversion backend modules.
