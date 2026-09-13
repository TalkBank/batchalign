# CHAT handling by the pipeline

The Rust core uses TalkBank's CHAT model and parser. File input conversion enters
through `Chat::parse`; task runners operate on the resulting typed state, and
outcome writing serializes it. Python CLI code owns path selection and may stage
input text before the Rust parse.

For morphology, staging removes existing `%mor`/`%gra` by default, while
`--keep-existing` retains them. Translation emits `%eng`. Transcription creates
a new transcript from media. See [Command I/O](command-io.md) for the complete
input/output table and [Morphosyntax](morphosyntax.md) for tier alignment checks.

For CHAT syntax, use the shared [CHAT format reference](../../chat-format/overview.md).
The old Rust-server parse-mode table does not describe this pipeline entrypoint.
