# Processing provenance comments

Successful CHAT pipeline outputs contain a comment for each task in the
pipeline's task order. The current shape is:

```text
@Comment: batchalign3 <compiled-git-sha> | <task>: <backend-name> | <UTC timestamp>
```

The placeholders above describe fields, not a literal header to add yourself.
The backend name can encode model/runtime versions and settings. A missing
backend name is recorded as `<unknown>`.

When a matching `batchalign3` comment for the same task is present, stamping
replaces it in place. Comments for other tasks are preserved. Failed pipeline
outcomes are not stamped as successful output for the whole task sequence.
This records the pipeline configuration, not proof that every backend request
ran freshly: [cached results](caching.md) may have been reused.

ASR-generated transcripts also include `@Comment: Unchecked output of ASR model`.
This is separate from build/task provenance and signals that the transcript
needs review.

Implementation: engine `pipeline.rs::stamp_run_provenance` and core
`utils.rs::stamp_provenance`. The earlier bracketed `[ba3 command | ...]` examples
are not the format emitted by this implementation.
