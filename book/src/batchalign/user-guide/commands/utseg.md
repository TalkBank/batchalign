# Segment a transcript into utterances

Use `utseg` when a CHAT transcript needs utterance boundaries revised.

```bash
batchalign utseg corpus/ -o segmented/
```

Open the output and check the new boundaries against the conversation. Without
`-o`, the command updates source files in place.

The CLI uses the CHAT utterance-segmentation backend. The `--language` option
is passed to that backend and defaults to `en`. To enable its Stanza fallback:

```bash
batchalign utseg corpus/ -o segmented/ --stanza-fallback
```

See [CLI reference](../cli-reference.md#utseg) for device options. Backend results
use the [result cache](../caching.md).
