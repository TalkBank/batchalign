# Release notes

## 0.10.10

This release includes the latest desktop runtime fixes and aligns the application
and Python package versions.

- Intel macOS runtime validation no longer mistakes Cryptography’s own library
  name for an external dependency. Runtime build errors retain their diagnostic output.
- macOS worker cleanup handles process groups that have already exited.
- Desktop validation covers Windows x86-64, macOS on Apple silicon and Intel,
  and Linux x86-64 and ARM64, including installed application checks.

The application installers are available from the [homepage](../index.md) and
[GitHub releases](https://github.com/TalkBank/batchalign/releases). Update the
Python package with:

```bash
pip install --upgrade batchalign
```

## Included from 0.10.9

- Optional [AVQI analysis](user-guide/commands/avqi.md) with
  `pip install 'batchalign[avqi]'`, paired vowel and speech inputs, mirrored
  directory matching, and CSV output.
- Pasketti engine options for [word transcription](user-guide/commands/transcribe.md)
  and [phonetic transcription](user-guide/commands/phonetic.md).
- Plain CLI headers compatible with legacy Windows output encodings.
- Clean-install AVQI checks for all five wheel platforms.
