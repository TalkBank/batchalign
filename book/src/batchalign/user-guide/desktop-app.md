# Run the desktop application from source

The Batchalign desktop application lives in `apps/batchalign/batchalign-gui/`.
It uses React and Tauri, with a bundled Python HTTP-service sidecar.

From a development checkout with the repository build tools installed:

```bash
just batchalign gui dev
```

The Bazel dependency graph builds and stages the sidecar. To create a desktop
bundle, use `just batchalign gui build`.

In the application, drop an input folder onto the window or choose **open
folder**, add a command, review its language and engine settings, choose the
output location, and start the batch. Folders are searched recursively.
The app displays one folder at a time. Use **choose…** to replace it or **close**
beside the folder chooser to return to the drop-folder screen.
The **speaker** command and **Speaker recognition** option identify speaker
turns. The elapsed timer continues updating while a model is busy.

For transcription, enter a valid three-letter ISO 639-3 language code before
choosing an engine. Autocomplete searches codes and language names; Chinese uses
`zho`. No ASR engine is selected automatically. Recommendations appear in a gray
box, with the other engines listed below: CHAT-Whisper for English; Aliyun for adult Cantonese
and FunASR/SenseVoice for child Cantonese; Paraformer-zh for Mandarin. Google
GenAI, OpenAI Whisper, Qwen3, and Rev.AI are the general choices. Rev.AI is always
offered after a valid language is entered; other engines follow service availability.
Recommendations include cloud and local choices, with cloud engines first.
Rev.AI supplies the cloud recommendation when there is no language-specific one;
OpenAI Whisper or Qwen3 supplies a local fallback when available.
The **Recognition engine** defaults to pyannoteAI (cloud).
The GUI omits Malayalam Wav2Vec,
Qwen, Tencent Cloud ASR, and Hugging Face Whisper; their CLI/API availability
is unchanged.

For ordinary command-line use, start with the [Quick Start](quick-start.md).
The CLI does not require the desktop service to be running.
