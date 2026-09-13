# Add translation tiers

Use `translate` to add translation text to CHAT transcripts:

```bash
batchalign translate corpus/ -o translated/ --target eng
```

The default engine is Google. Open the output and review the `%eng` tiers. The
current output tier name remains `%eng` even when another target language is
selected. Without `-o`, the command updates source files in place.

To select the local NLLB backend:

```bash
batchalign translate corpus/ -o translated/ --target eng --engine nllb
```

The other CLI engine choices are `tencent` and `aliyun`. Provider setup and
language coverage depend on the selected backend. See
[CLI reference](../cli-reference.md#translate) for options.
