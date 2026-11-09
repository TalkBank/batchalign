# Related tools and documentation

This repository ships Batchalign: the Python CLI and backends, Rust processing
engine, HTTP service, and Batchalign desktop application. It does not ship CLAN,
the Chatter CLI or desktop application, a CHAT language server, or a VS Code
extension.

## Chatter and CHAT-format tools

[Chatter](https://github.com/TalkBank/chatter) owns the CHAT parser, typed model,
validation, transformations, CLI, language server, and Chatter desktop app.
Use its [documentation](https://talkbank.github.io/chatter/) for installation,
validation, parser development, and editor integration.

Batchalign consumes versioned Chatter crates. See the
[Batchalign source map](batchalign/developer/rust-workspace-map.md) for the
dependency boundary. The [CHAT-format reference](diataxis/chat-format-reference.md)
in this book explains transcript notation used by Batchalign; the
[CHAT manual](https://talkbank.org/0info/manuals/CHAT.html) is the format reference.

## CLAN

For CLAN analysis commands and their options, use the
[CLAN manual](https://talkbank.org/0info/manuals/CLAN.html).
The former Rust CLAN command manual described code that is no longer in this
repository. Its commands are not Batchalign commands, and Batchalign releases
do not provide a CLAN executable.

## Editors

For editor support backed by Chatter's language server, follow
[Chatter's editor documentation](https://talkbank.github.io/chatter/).
The former VS Code extension manual in this book described a separate
application; Batchalign's desktop is documented in
[Desktop application](batchalign/user-guide/desktop-app.md).

## Older documentation

The former combined-toolchain manuals remain in
[repository history](https://github.com/TalkBank/batchalign/tree/8663a77b/book/src).
They describe the source tree at that revision and should not be used as current
installation or release instructions. Old published URLs redirect to current
Batchalign pages or to this page.
