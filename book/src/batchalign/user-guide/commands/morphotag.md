# Add morphology and grammar to a transcript

Use `morphotag` on checked CHAT transcripts to add `%mor` morphology and `%gra`
dependency tiers. Audio is not required.

1. Put the CHAT files you want to process in a folder. Check that each file's
   `@Languages:` header identifies its language.
2. Choose a separate destination folder, then run:

   ```bash
   batchalign morphotag "corpus" -o "tagged"
   ```

3. Wait for the final summary. The first use of a language can download Stanza
   models before tagging begins.
4. Open a transcript in `tagged` and inspect its `%mor` and `%gra` tiers under
   the speaker lines. Review the analysis before using it in your workflow.

Without `-o`, this command updates source files in place. Folder input is
recursive. You can also supply individual files or an
[input list](../cli-reference.md#input-selection).

## Retag existing analysis

By default, the CLI removes existing `%mor` and `%gra` tiers from staged inputs
before processing. Matching backend results may still come from the result cache.
To preserve existing analysis and let the engine skip already-tagged utterances:

```bash
batchalign morphotag corpus/ -o tagged/ --keep-existing
```

## Allow retokenization

If you need the backend to retokenize text, request it explicitly:

```bash
batchalign morphotag corpus/ -o tagged/ --retokenize
```

Check the resulting main tiers as well as the analysis tiers.

For options, see [CLI reference](../cli-reference.md#morphotag).
For reuse and speed, see [Caching](../caching.md) and [Performance](../performance.md).
