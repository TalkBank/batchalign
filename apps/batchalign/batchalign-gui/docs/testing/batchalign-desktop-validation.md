# Desktop cleanroom validation

Completion requires an installed desktop bundle, after macOS quarantine/signing
bypass where necessary, to start and execute every supported GUI pipeline
correctly. Build success, a health check, or mocked backends do not prove pipeline
correctness. Preserve the existing interface. Run heavy builds and model
installations on GitHub runners; local tests use one worker.

## Required evidence

- Native packages: macOS arm64/x86_64, Linux arm64/x86_64, Windows x86_64.
- Fresh install with isolated application/PyApp/model/config caches; visible
  bootstrap progress, capabilities handshake, warm relaunch, failure diagnosis.
- All six GUI steps (transcribe, diarize, align, morphotag, translate, compare),
  selectable backends and supported compositions, checked against actual output
  artifacts. Include output directory/in-place mode, nested paths, Unicode,
  progress, errors, settings, restart/retry behavior.
- GUI unit tests, property tests, seeded randomized interactions/events.
- Native IPC, HTTP relay and SSE tests in installed packages, beyond browser
  tests that stub Tauri. Pipeline correctness requires real model/provider tests.
- Retain CI logs, reports and screenshots/traces for review.

## Evidence and implemented fixes (2026-09-20)

- Starting worktree: 46be801. Its published build run 34803282092 succeeded for
  macOS arm64/x86_64 and Linux x86_64, but tested no installation or pipelines.
- Startup fix 3b51189: all eight jobs of GUI CI run 35536631215 passed
  (Chromium/WebKit, both Mac architectures, Linux x86_64, Windows x86_64).
  Fixed missed warm-start readiness and listener teardown/remount races. Added
  100 seeded lifecycle sequences and 500 tab-action sequences.
- Desktop jobs now execute every selected recipe in order, stage intermediate
  CHAT files, retain original absolute source IDs for native media resolution,
  map progress to GUI-relative IDs, and publish output transcripts/compare CSV.
  In-place originals survive failures. Output/worker/device/cache/gold/aligner
  settings are transmitted. Gold files and media are not alignment/comparison
  primary inputs. Submission errors reach existing file logs; duplicate starts
  are latched; status polling provides terminal state if SSE closes early.
- Corrected native callback list shape and PyO3 progress enum serialization;
  failed native outcomes no longer count as successful jobs. Cancelled workers
  retain their staging files until exit. Removed zero-duration SSE timeout and
  stopped SSE connection failures from marking the entire daemon failed.
- Current local frontend: 16 unit/property tests and 10 Chromium GUI tests pass
  (all six individual steps and a four-step chain; GUI boundary is mocked).
- Added 1,000 seeded mixed progress sequences checking batch isolation,
  terminal-file stability, stale jobs and percentage bounds. Fuzzing found
  negative progress percentages (minimal completed=-1, total=1); fixed with
  bounded finite progress handling. Production frontend build also passes.
- GUI CI run 35537862881 passed all ten Chromium/WebKit jobs across Linux
  arm64/x86_64, macOS arm64/x86_64, and Windows x86_64 at revision 751d666.
- Native startup now retains its child for timeout/error/app-exit cleanup,
  remembers failures that precede frontend listeners, and clears dead daemon
  handles. Environments are isolated by SHA-256 of the embedded sidecar rather
  than deleting other installed versions. Four standalone Rust protocol tests
  pass, including all 65,535 valid ports and bounded large Unicode diagnostics.
  Full native state/process tests are wired into bundle CI and remain unverified.
- Focused Bazel pytest: native CompareBackend runs on a valid corpus excerpt,
  produces CHAT + metrics, and verifies WER=0 / accuracy=1 for identical inputs.
  Native invalid-CHAT test confirms failure diagnosis and no overwrite. Other
  orchestration tests use fake pipelines and do not prove ML correctness.
- Smoke harness validated through `just batchalign cli daemon`: two launches,
  real HTTP/SSE/native comparison and output preservation pass. Report:
  /tmp/batchalign-cli-smoke-report.json. This is explicitly CLI-harness mode,
  not evidence of packaged bootstrap.
- Added CI bootstrap checks against the sidecar extracted from real bundles:
  isolated cold/warm PyApp environment + native comparison. Windows and Linux
  arm64 added to native bundle matrix; Windows executable suffix handling added.
  These new matrix gates still need run evidence.
- Previously published macOS arm64 bundle downloaded to
  /tmp/batchalign-cleanroom-34803282092. Do not bootstrap its ML dependencies
  locally; use disposable CI runners.

## Remaining work / findings to verify

- Run and fix the expanded CI bundle/bootstrap matrix, including Windows build
  portability. Add installed native-webview automation (not just sidecar tests),
  installation/quarantine handling, and real-model/provider pipeline matrix.
- Linux CI now installs the generated .deb and drives the unmodified app with
  tauri-driver/WebKit: two native launches, overlay readiness, real folder scan
  and HTTP IPC comparison, correct CHAT/metrics, screenshots, and daemon exit
  after window close. It reuses this bundle's isolated warm PyApp environment
  from the preceding cold/warm sidecar test. Syntax checked, not yet executed;
  native cold bootstrap and Windows/macOS webview automation remain due.
- Windows native-webview CI now installs the MSI into a path containing spaces,
  installs a pinned WebView2-matching Edge driver helper, and runs the same
  unmodified-app readiness/IPC/output/shutdown/relaunch script. MSI logs and
  screenshots are retained. This is configured but not yet executed; macOS
  needs a separate native automation implementation.
- First Windows bundle job 106150069980 (run 35537862870) compiled the wheel
  and PyApp, then failed because the declared extensionless `sidecar` output
  was missing. MSYS executable-copy suffix behavior is the suspected cause:
  wrappers now write the exact declared binary output with shell redirection,
  for both PyApp and cargo-tauri. Shell syntax checks pass; Windows CI must
  confirm the fix. Full failed-job log: /tmp/batchalign-windows-job.log.
- Linux ARM64 job 106150069976 compiled successfully but AppImage packaging
  failed because /usr/bin/xdg-open was absent. Added xdg-utils to Linux runner
  prerequisites. Verification is pending the next matrix; complete log is
  /tmp/batchalign-linux-arm-job.log.
- Linux x64 job 106150070004 passed packaged-sidecar checks at 751d666:
  cold bootstrap 225.283s, warm launch 0.610s, real comparison CHAT + CSV with
  WER=0 / accuracy=1, input preservation and SSE completion. Downloaded report:
  /tmp/batchalign-linux-x64-runtime-35537862870/packaged-sidecar-report.json.
  This predates the native-webview/model test additions and does not prove them.
- macOS QA native-webview support uses optional `webdriver` Cargo feature and
  a separate capability config. CI builds an instrumented executable after the
  production .app, copies it into a separate QA .app, clears xattrs/ad-hoc signs,
  and runs the shared native smoke through embedded WKWebView WebDriver.
  Production bundle artifacts remain uninstrumented. Dependency resolution and
  script syntax checks pass; actual macOS test build/execution remain pending.
- Added real-model checks to each packaged-runtime job: default Whisper
  large-v3 transcription of the 20-second English reference (WER <= 0.3 and
  timing required), default Wav2Vec2 FA (unchanged words, %wor, valid timing),
  local Pyannote single-speaker diarization (no word/utterance loss), and live
  Google translation of two Spanish sentences (meaning assertions). These run
  one at a time on CPU with independent failure records; existing GUI checks
  exercise real Stanza plus comparison afterward. Reports retain actual CHAT
  outputs, model kwargs, timings and errors. Syntax checked only; real inference
  is pending CI, and provider-specific alternatives still require coverage.
- Verify native supervisor changes in bundle CI, including subprocess cleanup
  during PyApp bootstrap (the direct-child test alone cannot prove descendant
  cleanup). New environment isolation leaves old versions available; their
  disk usage needs an explicit, safe retention policy if automatic pruning is
  introduced later.
- Replaced stale gui.spec.ts with an actual morphotag → compare GUI workflow,
  requiring real CHAT morphology/dependency/comparison tiers and WER=0 /
  accuracy=1. The packaged-sidecar harness runs it against its live warm daemon
  when BATCHALIGN_SMOKE_GUI=1; bundle CI installs Chromium and retains output
  attachments/screenshots/traces. Test discovery passes; real-model execution
  remains due in CI. This still stubs native IPC and the OS folder picker.
- Status polling now retries transient failures without resubmitting the job;
  two tests verify recovery and bounded persistent-failure diagnosis.
- Native SSE relay now observes replacement and daemon shutdown while connecting
  and streaming, checks HTTP errors, and uses identity-checked cleanup so an old
  pump cannot unregister its replacement. Added a native replacement-ordering
  regression test; full native CI execution remains due. SSE connection/headers
  are bounded separately from the long-lived event body.
- Extracted native HTTP relay has a 30-second total request deadline, bypasses
  environment proxies for loopback, and aborts when its daemon stops. Two Rust
  socket-level tests pass via `just batchalign gui native-http`, covering JSON,
  empty responses, HTTP errors, malformed JSON, and a stalled response body.
- Shutdown state now persists even with no active watch subscribers, so a
  request that captured a daemon handle immediately before exit cannot miss
  the failure when it subscribes afterward. Added a native late-subscriber
  regression; full native unit execution remains pending package CI.
- Changing the first pipeline step now refreshes folder discovery, so completed
  transcription can be followed by alignment of newly created CHAT files.
  Stale scans are ignored and pipeline edits are rejected during running jobs.
  Local validation passes: 17 unit/property tests, 11 Chromium GUI tests, and
  the production frontend build. The new GUI regression uses mocked native IPC;
  installed-app inference remains a separate CI gate.
- Settings still need complete mapping: memory/adaptive-worker controls,
  stored Rev.AI key, and skip-code-switching semantics. Stanza now accepts
  device selection, forwards it to single/multilingual pipelines, and includes
  device in its cache key so force-CPU cannot reuse an automatic-device model.
  Focused tests cover this and the desktop force_cpu/worker forwarding path.
  Other global/local models still need a force-CPU audit.
- In-place .chat suffix preservation has a regression test; only media inputs
  switch to the .cha output suffix.
- Native comparison CSV file labels previously appended .cha to absolute CHAT
  paths (yielding .cha.cha); fixed with a native integration assertion.
- Standalone desktop alignment previously omitted UTR entirely. It now adds
  a lazy local Whisper timing-recovery backend when none is explicitly given;
  force-CPU is forwarded, and model construction is deferred until dispatch.
  Focused orchestration/laziness tests pass (17 tests including desktop jobs).
  Native timed-input skip now passes an integration test with zero Whisper
  construction; native untimed recovery correctly dispatches controlled ASR
  output, writes 100_700 timing and removes the unlinked media status. Four
  timing tests pass. Actual untimed-media model accuracy remains unverified;
  the controlled ASR result does not prove inference correctness.
- CI provider-secret listing was empty. Need live-provider credentials/test
  strategy; do not count fake services as provider correctness. There is ample
  independent work before this can constitute a blocker.

The real-model CI harness stops the daemon if submission/polling fails before
a terminal job state is confirmed, preventing a still-running model from
overlapping the next test. A lightweight fault-injection check verifies this
and verifies confirmed terminal failures still allow all remaining recipes.

Fresh-install transcription and diarization now default to local Pyannote;
the previous cloud default required credentials before ordinary speech jobs
could run. Explicit cloud selections remain supported. Unit coverage verifies
defaults and overrides (18 unit/property tests passing); real CI transcription
now includes local speaker diarization as the GUI does. GUI media discovery
also includes MOV/M4V, matching the desktop API and CLI extensions.

GUI stress coverage now performs 240 seeded pipeline add/select/remove actions
with repeated submissions and checks the exact ordered request and input type
after prior runs. All 14 Chromium GUI tests pass locally, including these three
seeds; the production frontend build passes. This uses mocked IPC and does not
prove model inference. Transcription is now offered only as the first step,
matching the desktop API rather than letting users build a rejected chain.

Native lifetime test audit found a call to the shell plugin's private
Command::new constructor. It now creates a mock Tauri app with the shell
plugin and uses the public ShellExt::command API to launch the real child.
The Tauri test feature is development-only. Cargo manifest metadata resolves;
full native compilation and execution remain due in CI.

Additional authoritative packaged evidence: run 35537862870, SHA 751d666,
macOS ARM64 report downloaded from packaged-runtime-aarch64-apple-darwin.
The sidecar inside Batchalign.app bootstraps cold in 138752 ms and warm in
482 ms, then writes real comparison CHAT/CSV with WER 0 and accuracy 1,
correct Unicode filename, source preservation, and terminal SSE events.
This old revision does not include full-model or native-webview gates and
must not be cited as evidence that those passed.

Intel macOS packaged bootstrap in run 35537862870 failed before daemon
startup: pip selected Numba 0.67/llvmlite source distributions, then llvmlite
failed to compile because LLVM was unavailable. Verified PyPI CPython 3.12
Intel macOS wheels exist for numba 0.62.1 and llvmlite 0.45.1. Added a
macOS-x86_64-only Numba <0.63 constraint to speech extras and NumPy <2
for the available Torch 2.2 wheel ABI. Regenerated Python locks via just;
focused desktop_jobs Bazel tests pass. Intel cleanroom bootstrap needs rerun.

Expanded browser matrix run 35541484110 (29f4828b): nine jobs passed.
Windows WebKit completed all 14 tests successfully (including all three
stress seeds), but its Playwright worker failed to exit within 300 seconds,
so the job is correctly red. Re-ran only the failed job with GitHub runner
diagnostics; teardown outcome is pending. Native run 35541484100 is live
on all five targets and must not be restarted just because builds are slow.

Added a bounded native malformed-input smash test: 51 valid/corrupted CHAT
inputs (seed 20260920, byte splicing including invalid UTF-8, NULs, tier and
timing fragments) run through the real desktop endpoint, compiled comparison
parser, and writer with two workers. It passes: every source is preserved,
every non-completed output retains its previous contents, valid members
complete, and a subsequent clean job succeeds. No ML models are downloaded
for this test; it is parser/orchestration evidence, not inference accuracy.

Native-webview harness now allocates its own fresh PyApp install directory
and waits through cold bootstrap in the actual webview. It records visible
progress lines and a screenshot, fails promptly on the existing startup error
overlay, requires at least one cold progress update, then checks native IPC,
comparison, app exit, and warm relaunch using that same environment. Native
steps allow 30 minutes for this additional cleanroom install. Syntax checks
pass; actual cold-webview execution is still due in CI.

Windows WebKit diagnostic job 106162969667 in run 35542394739 passed
all 14 GUI tests and clean teardown. Browser logs show graceful close started
at 22:48:29.770Z and finished at 22:48:29.782Z, process exit code 0. Earlier
non-diagnostic runs hung at worker shutdown; the root cause is not established
by this passing run. Keep browser logging and preserved-running-job CI policy.

Run 35541484100 macOS ARM job 106159916202 compiled the complete Tauri
release app successfully, then failed in bundle_dmg.sh after four seconds.
Default Tauri logging hid the script stdout/stderr; CI now enables --verbose
and retains partial bundles/scripts on failure. The DMG failure remains
unresolved until detailed diagnostics or a successful installer run exists.
Native unit/model gates were skipped in that failed job; do not count them
as passing. Other platform jobs in this run remain live.

GUI matrix 35542394739 completed successfully across all ten platform/browser
jobs (macOS ARM/Intel, Linux ARM/x64, Windows; Chromium and WebKit), including
18 unit/property tests and 14 GUI tests per job. This verifies mocked-IPC
frontend behavior, not installed inference. Native run 35541484100 Linux ARM
passed packaging and native regression tests and entered real runtime checks;
Linux x64 has also advanced past packaging/native tests. Full reports pending.

Real Linux runtime reports from 35541484100 are now available for both
architectures: cold/warm startup and native comparison pass, and real
Wav2Vec2 alignment passes. Transcribe and diarize fail because Pyannote 4
attempts gated community-1 PLDA downloads while loading the public TalkBank
3.0 config. Real GUI morphotag→compare has %mor and correct WER, but loses
%gra; investigate pipeline/writer behavior rather than weakening the assertion.
Translation echoed Spanish instead of English. A local authoritative CLI run
reproduced that false success. googletrans defaults to fabricated echo output
on HTTP errors; now it raises, uses bounded HTTP timeouts, closes each client,
and has a v2 cache identity to invalidate bad cached echoes. Four real-client
mock-HTTP tests pass. A fresh CLI run correctly fails with HTTP 429; successful
translation remains unverified and must still be achieved. Reports are in
/tmp/batchalign-{aarch64,x86_64}-runtime-35541484100 locally.

Do not mark the goal complete until all required platform/pipeline gates have
passing evidence. Existing tests and new configuration alone are insufficient.

Follow-up fixes awaiting installed CI evidence:
- Pin the public dia-fork pipeline to pyannote.audio 3.4.x and torch/torchaudio
  below 2.9. Pyannote 4 eagerly fetches community-1 PLDA even though this
  agglomerative pipeline does not use it (upstream issue 2044); Pyannote 3
  requires the AudioMetaData/info APIs removed in TorchAudio 2.9.
- The missing final %gra is intentional: compare.rs strips grammar tiers to
  match BA2. The real GUI test now checks standalone morphology's %mor/%gra
  first, then reruns the ordered morphotag→compare chain and verifies its
  %mor/%xs output, absent %gra, preserved gold, and exact comparison metrics.
- Windows run 35541484100 built the MSI, but native unit execution failed
  before any test with STATUS_ENTRYPOINT_NOT_FOUND (0xc0000139). Add the
  Common Controls v6 manifest to native test executables, following Tauri's
  upstream issue 13419/workaround. This is not yet verified on Windows.
- Independent installed/runtime checks now execute after unrelated native
  unit or model failures when packaging succeeded; failures still fail CI.
Local validation: 20 focused desktop/translation Python tests and 18 GUI
unit/property tests passed; frontend production build passed. No local ML
models or full desktop build were downloaded/run for these changes.

Installed-runtime smash coverage now runs before ML tests on every target:
259 cases (65 structurally valid comparison/writer variations, 194 malformed
cases from three seeds), five invalid API requests, source/gold preservation,
no partial publication over previous outputs, and a subsequent successful job.
Local authoritative CLI harness validation passed with exactly 65 completed
outputs, 194 preserved failures, and successful recovery; evidence:
/tmp/batchalign-smash-cli-report-v2.json. Packaged cross-platform execution is
still pending. The model harness also now tests actual NLLB translation in
addition to Google; neither backend's success is assumed. Dependency and
Python packaging changes now trigger the desktop matrix directly.

Pyannote 3.4 calls Lightning's checkpoint loader without weights_only, which
inherits Torch 2.6+'s restricted default. Static inspection of the public
seg-fork-3.0 checkpoint's first 64 KiB (no tensor weights loaded) found four
metadata globals beyond Torch's ordinary tensor types: TorchVersion,
Specifications, Problem, and Resolution. Scope those four known types to
Pipeline.from_pretrained via torch.serialization.safe_globals. Do not disable
restricted loading globally. Two focused tests use real torch.save/load with
weights_only=True and verify allowlist restoration after success and failure;
both pass through just batchalign pytest. Actual model inference still awaits CI.

Translation cache audit found that the runner's target hint stays eng while
Google/NLLB constructor targets override it. Include target in both backend
cache identities (and NLLB's generation length). A real native Pipeline/LMDB
regression runs eng→fra→eng, verifies the emitted language each time, and
proves the final English run reuses only the English result. Five focused
translation tests pass. NLLB now explicitly requests safetensors: the official
model repo's SFconvertbot PR 5 is based on current main and contains the
converted weights; Transformers 4.57 resolves this existing conversion. This
avoids its pickle fallback, which Intel macOS's Torch cannot load through
current Transformers. Successful cross-platform NLLB inference still pending.

Full local Python suite at 3af90b52: 469 passed, 3 skipped (9.78s test time,
one Bazel worker). GUI run 35544106045 passed all ten jobs, but subsequent
35544327930 again failed only Windows WebKit teardown after all 14 assertions
passed. With browser diagnostics, host PID 716 was already absent when
Playwright tried taskkill; its child-process close event never arrived, and
runner cleanup found orphan conhost processes. This is an intermittent test
browser lifecycle problem, not an assertion pass. Upgrade Playwright 1.60 to
1.63 and add read-only Windows WebKit exit/close/stdio/process diagnostics;
do not suppress teardown failures. Updated tooling passes 18 unit tests,
production frontend build, and test discovery locally; no new local browser
binaries downloaded. CI now caches Cargo dependencies (including on later
runtime failure), because the Tauri Cargo build is outside Bazel's cache.

Folder discovery no longer silently leaves start disabled on a scan error:
retry three times with bounded delays, then show the error in the existing
placeholder. Reopening the folder or changing the first step permits recovery;
stale failures cannot override a newer request. Nineteen unit/property tests
and the production build pass. The focused browser recovery test also passed
using the already-cached Chromium 1234 binary with Playwright 1.63; CI still
must verify its own pinned browser binaries. Compare's obsolete ROOT-head
comments were corrected: the current morphology renderer already preserves
head zero; grammar removal remains the deliberate comparison output contract.
Intel macOS in 35541484100 now passed packaging and native regression tests
and entered real runtime checks. Full inference results remain pending.

Additional diarization accuracy gate: Pyannote's public 30-second, two-speaker
sample and its 13 timed reference turns, pinned to upstream commit
b749285c5cdd4636b2edc7f766f1352c8dde9369 with SHA-256 checks. CI downloads
under 1 MB of fixtures and runs the actual Pyannote backend with two speakers.
Require preserved words/source, two distinct output labels, and at least 80%
word-level speaker agreement after choosing the better label permutation.
Compare per word so legitimate native turn splitting remains allowed. Syntax
checked only so far; real accuracy must be established in the installed matrix.
Local full GUI interactions after folder-recovery changes: all 15 passed with
the already-cached Chromium 1234 browser. Windows Chromium and WebKit jobs
106169519495/106169519487 passed using Playwright 1.63; WebKit PID 3052 emitted
exit and close with code zero, all streams destroyed, and graceful shutdown
finished in 15 ms. One passing run does not prove the prior flake eliminated.

Intel macOS 35541484100 finished: packaging and all 10 native unit tests pass;
cleanroom bootstrap 441108 ms, warm restart 1168 ms, comparison passes. Real
Wav2Vec2 alignment, Pyannote diarization, and Google translation all pass
(including actual English red-apple/song output). Transcription fails with
LayerNormKernelImpl not implemented for Half on Torch 2.2 CPU. Whisper now
requests float32 at load time for explicit or automatically selected CPU,
avoiding a second in-memory model copy; accelerator auto dtype is preserved.
Its cache identity now includes the constructor language hint. Seven focused
device/kernel tests pass without downloading Whisper. Actual fixed inference
still needs installed CI. The old GUI failure is the known final %gra assertion,
already replaced by separate standalone-morphology and comparison checks.
Report: /tmp/batchalign-mac-intel-runtime-35541484100/packaged-sidecar-report.json.
Run 35545692852 (483ec5b8) has begun the expanded matrix, predating this CPU
fix; retain its independent native/model evidence and build caches.

Run scheduling correction: after confirming CPU fix 6c8397f1 and its seven
focused tests, 35545692852 was still entirely in setup/sidecar compilation
(no new runtime evidence). Cancelled that early run so queued 35545849846 can
validate the fixed revision across all targets. Preserve the completed
35541484100 reports; the cancellation was for the confirmed CPU defect,
not a build timeout or local resource shortage.

Playwright 1.63 macOS 14 WebKit job 106169519499 failed before page creation:
Page.overrideSetting rejected Unknown setting: PushAPIEnabled. macOS 14 uses
frozen WebKit 2251; this is a driver/browser mismatch, not an application
assertion. Evidence includes trace/error-context artifacts at
/tmp/batchalign-macos14-webkit-163-evidence and the full job log locally.
CI-only commit cba9aba0 retains all ten platform/browser jobs but installs
Playwright 1.60.0 for macOS 14 WebKit, the pairing that previously passed.
All other jobs use 1.63. The installed-app matrix 35545849846 stays on
6c8397f1 (same application source as cba9aba0) and is not restarted.
Full local Python suite with CPU fix: 476 passed, 3 skipped (9.80s test time).

GUI run 35545849839 (CPU-fixed app) completed all six Linux/Windows jobs
successfully, including 19 unit/property + 15 GUI tests and a second clean
Windows WebKit run (job 106172891647). Its four macOS jobs were still queued.
Cancelled only this stale GUI run to advance corrected pairing run
35546446892; no running macOS GUI test evidence was discarded and installed
matrix 35545849846 continues unchanged.

Real local bounded Whisper inference: default CPU and explicit Apple MPS both
completed the committed 20-second English fixture with Whisper-tiny, correct
future-leaders content and word/utterance timing (22.3s CPU, 11.1s MPS).
Ran via just batchalign cli daemon and the real desktop job API, no provider
mocks. Default device now explicitly selects CUDA when available, otherwise
CPU; MPS remains opt-in as documented by the CLI. Seven device tests pass.
The isolated 148 MB model cache was deleted after stopping the daemon and
verifying its PID/listening port were gone. This tiny-model check does not
replace default large-model or packaged native-webview CI. Evidence retained
at /tmp/batchalign-whisper-device-check/report.json.

Expanded installed-model gate also submits a timestamp-free copy of the
English alignment fixture with unlinked media. It uses the actual default
Whisper-large-v3 timing recovery followed by Wav2Vec2 forced alignment.
Require all three utterances and words preserved, three word-timing tiers,
ordered bounds inside the recording, more than 15 seconds of recovered
coverage, linked media, and byte-preserved source. Script syntax checked;
actual inference result remains pending on GitHub CI.

GUI matrix 35546446892 at cba9aba0 passed all ten OS/browser jobs, including
macOS 14 WebKit with its compatible 1.60 driver: 19 unit/property and 15 GUI
tests per job. Windows native loader fix also passes all ten native tests
in 35545849846. Apple Silicon DMG packaging passed this run; the older
transient DMG failure did not recur, so its precise old cause remains unknown.

Linux ARM64 installed runtime 35545849846: cold bootstrap 134898 ms, warm
564 ms; comparison, all 259 smash samples (65 complete / 194 preserved
failures), malformed-request rejection and following-job recovery pass.
Real FA, single-speaker diarization, two-speaker diarization (98.765% word
speaker agreement), Google translation, NLLB translation, and real GUI
morphology then morphology-to-compare all pass. Transcription fails CHAT
validation E704: one speaker's consecutive utterances overlap by 1000 ms.
A local native ASR-to-CHAT regression reproduces the same failure from a
small synthetic Whisper response, without downloading model weights.
Whisper now projects its ordered word boundaries to the closest monotonic
sequence, preserving text and already-valid timings. This repair is local
to Whisper, not concurrent speakers from other providers. Clamp to the
recording bounds, reject non-finite timestamps, and invalidate both ASR
and desktop timing-recovery caches. The native regression now passes;
real repaired large-model inference remains a required CI result.

Linux ARM64 native webview step installed the Debian package successfully
but exited before invoking the driver: its tar-listing parser required a
'./' path prefix, while Tauri's tar builder writes relative paths without
it. Query dpkg's installed file list for the absolute GUI executable,
excluding the sidecar, instead of parsing dpkg-deb display output.
Evidence: /tmp/batchalign-arm-runtime-35545849846/packaged-sidecar-report.json
and /tmp/batchalign-arm-native-35545849846.log. Native webview still pending.

Timestamp validation: all 27 Whisper-related tests pass, including the
real native serialization regression, an exhaustive four-boundary
least-squares oracle, and 1000 seeded ordering/bounds/idempotence checks.
Full Python suite after the repair: 479 passed, 3 skipped. No model weights
were downloaded for these checks.

Scheduling at fe961c7e: installed validation now queues independently per
target, preserving active jobs while completed targets advance. New run
35548718605 tests the timestamp/launcher fixes. Superseded pending native
35548634962 was cancelled before execution. Duplicate GUI runs 35547404872
and 35548635041 were cancelled; frontend code remains identical to the
all-ten-passed cba9aba0 matrix, and the cancellations free macOS runner
slots. Older native 35545849846 continues independently for remaining evidence.

Windows runtime 35545849846: cold bootstrap 330567 ms, warm 817 ms; compare,
259-input smash and recovery, real FA, both diarization fixtures (98.765%
word speaker agreement), and Google translation pass. Transcription has
the same 1000-ms overlap regression now fixed. NLLB loses the HTTP connection
(TypeError: fetch failed); its worker termination is unconfirmed, so the
harness correctly stops the daemon before attempting another model or GUI
job. This is NOT an NLLB pass, and its cause is not yet known. The next run
records child exit codes, cause chains, Python fatal traces, and Windows
crash/resource events. Release idle Bazel server memory before model tests
using just batchalign shutdown; cached outputs remain intact. The updated
harness passes locally through the authoritative CLI with all 259 samples,
two requested process stops, and no error. Evidence:
/tmp/batchalign-process-diagnostics-cli.json and
/tmp/batchalign-windows-runtime-35545849846/packaged-sidecar-report.json.
The local test daemon and Bazel server are stopped; no local ML download.

Shutdown audit: current native tests prove direct daemon termination after
readiness. They do not yet prove termination of every installer descendant
when closing during bootstrap; no unsupported claim of that coverage.

Linux x64 runtime 35545849846 also passes FA, both diarization fixtures,
Google/NLLB translation, comparison and the 259-input smash. Transcription
has the same known overlap. The real GUI test exposes a separate race:
SourceCompleted marks the entire batch done before terminal status polling
releases its submission latch. A quick second click is ignored. Reproduced
locally (expected running, got done), then fixed by letting only
BATCH_FINISHED conclude a job; file events update file rows only. The new
unit regression and deterministic GUI case verify completed-file / still-
running-job behavior and a successful second batch. Twenty GUI unit tests
and all 16 local browser cases pass using cached Chromium 1234 (12 pipeline
cases, 3 startup cases, and the new race case run separately).

Windows native 35545849846 installed its MSI and opened the unmodified
native WebView2 app into a ready screen, but cold startup showed no progress
for four minutes. Inspection of pinned PyApp 0.27 process::wait_for confirms
it captures all installer output until EOF, while indicatif hides its spinner
on pipes. This is an application packaging defect, not a reason to relax the
progress assertion. The Bazel PyApp source staging now announces the phase
and forwards installer bytes immediately while preserving captured error
output and UTF-8 decoding. The patch checks both exact pinned call sites
and fails if upstream changes. Two lightweight Bazel Rust tests pass,
proving output arrives before installer EOF and preserving Unicode split
across reads. No interface redesign or fake percentage was added.
Native evidence: /tmp/batchalign-windows-native-35545849846, including the
initial loading screenshot and the ready screen at failure. Updated real
native bootstrap and cross-platform browser results are still required.

Updated browser matrix 35549760205 (1ae02f0c): all ten jobs pass, each with
20 unit/property tests and 16 GUI tests. This includes the second-batch
race regression on Chromium and WebKit across all five native targets.
The PyApp patch also accepts CRLF source files while retaining exact
call-site checks (44b12355). Native matrix 35549839635 is still running.

macOS ARM runtime 35545849846: DMG packaging passes; cold bootstrap
117339 ms, warm 397 ms. Comparison, 259 smash inputs, FA, both diarization
fixtures, Google and NLLB translation pass. Transcription has the same
known timestamp overlap; real GUI fails before its second submission.
The instrumented native app reaches readiness but fails the cold-progress
gate, confirming the same PyApp buffering problem seen on Windows.
These older failures require actual passes with the repairs; they do not
count as successful native validation.

Windows process-tree audit: pinned PyApp's Windows exec implementation
waits on Python with command.status(), whereas Tauri shell CommandChild
kill terminates only the direct process. Stop the owned launcher with
taskkill /PID <pid> /T /F before the direct-child fallback, hiding the
utility's console window. Microsoft documents /T as including children:
https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/taskkill
A Windows native regression starts a TCP listener beneath a separate
PowerShell launcher, confirms it is reachable, stops the managed launcher,
and requires the descendant socket to close within five seconds. This
regression and actual installed-app shutdown still require Windows CI;
local formatting is not execution evidence.

Linux ARM64 native run 35549839635 (44b12355): cold sidecar bootstrap
131567 ms, warm 549 ms; all 259 smash inputs and recovery pass. Repaired
Whisper-large-v3 transcription now passes native serialization and WER
0.2222. FA, both diarization fixtures (98.765% word agreement), NLLB and
the real GUI morphology-to-compare flow pass. Untimed alignment exposes
another defect: UTR and FA only probe the transcript stem, unlike the
speaker runner's @Media-aware lookup. Share that lookup across all three
audio tasks and preserve dots in the media basename. A native Python
regression with recording.wav beside clip.cha reproduces the failure and
passes after the change. The updated full Python suite passes 482 tests,
with 3 existing skips; real repaired untimed inference remains pending.

Google translation in that run returns HTTP 429. Add bounded retries for
429/502/503/504, retain HTTP response headers, honor Retry-After, and fail
visibly after three attempts or a provider cooldown over 60 seconds.
Controlled HTTP tests prove eventual translation, delay handling, closed
clients, immediate 403 failure, and persistent errors never becoming echoes.

The unmodified installed Debian app now shows real installer progress and
completes native comparison correctly. Its shutdown gate fails after DELETE
session: that driver operation does not establish a normal window close.
The harness now explicitly closes the real window before session cleanup;
daemon shutdown and the following warm launch still require actual CI proof.
Evidence: /tmp/batchalign-arm-runtime-35549839635 and
/tmp/batchalign-arm-native-35549839635. No complete native-platform pass yet.

Windows runtime 35552384706 (e5272755): cold bootstrap 429391 ms,
warm 585 ms, all 259 smash inputs, transcription (WER 0.2222), and timed
alignment pass. Untimed alignment times out while fetching job status
after 30 seconds; the harness stops the daemon and does not run subsequent
model tests with an unconfirmed worker. The post-test Windows diagnostics
contain no crash or low-memory events. The timeout alone does not prove OOM.

The same run's installed MSI shows bootstrap progress and produces correct
comparison output, but still leaves its daemon alive on window close.
The Windows descendant cleanup unit test passes, exposing a lifecycle gap:
Tauri invokes plugin event handlers before the application callback, and
the shell plugin kills direct children on Exit. Move application cleanup
to ExitRequested so taskkill /T can still reach Python through its live
PyApp parent; retain idempotent Exit fallback and log taskkill failures.
Actual installed-app shutdown with this ordering still requires CI proof.

The runtime harness now checkpoints partial reports after bootstrap,
comparison, smash testing, and each real pipeline. Per-pipeline log markers
record start/outcome and system memory at start, so interrupted runs retain
more diagnostic evidence. These changes do not relax output assertions or
status deadlines. Evidence: /tmp/batchalign-windows-runtime-35552384706 and
/tmp/batchalign-windows-native-35552384706.

Apple Silicon runtime 35552384706 also fails during untimed alignment:
transcription passes (WER 0.2222, 1447120 ms), timed FA passes (36743 ms),
then the job-status connection resets. The harness requests shutdown and
requires SIGKILL after its grace period. Subsequent pipelines are not run.
Evidence: /tmp/batchalign-mac-arm-runtime-35552384706. Enable an opt-in
faulthandler watchdog around desktop timing recovery in the CI harness to
capture Python stacks during the stall; cancel it on both return and error.
No timeout or model-output assertion is relaxed.

The ARM retry 35554671549 again receives a runner shutdown signal shortly
after the MMS_FA download. Linux x64 job 106189398537 is terminal with a
GitHub annotation that its hosted runner lost communication; its log blob
is missing. These observations do not establish a memory-exhaustion cause.

Windows runtime 35557008512 (2c823add) passes transcription, timed and
untimed alignment, both diarization cases, and Google translation. Untimed
alignment takes 332086 ms and passes all preserved-word, media-header,
utterance/word-timing, duration, and source-preservation assertions. NLLB
then loses the daemon connection (ECONNREFUSED), so real GUI testing is not
run. This is the first real repaired untimed-alignment pass, not a full pass.
Evidence: /tmp/batchalign-windows-runtime-35557008512.

ARM runtime 35557008512 checkpoints show available memory falling from
15628283904 bytes before transcription to 8726319104 before timed FA and
6229377024 before untimed alignment. It receives another runner shutdown
signal 30 seconds into untimed alignment. The log is preserved at
/tmp/batchalign-arm-job-35557008512.log.

A model-free weak-reference regression establishes a native pipeline
lifetime defect: after deleting a pipeline and collecting Python garbage,
its backend remains alive. Rust runtime workers drop Py<Backend> without
the GIL; PyO3 queues the decrefs, retaining models until a later native
attachment. Pipeline Drop now takes its inner state, closes routes, and
joins the runtime while detached from Python. Reattachment flushes those
deferred references before the next Python model constructor can run.
Use try_attach for interpreter-shutdown fallback. The regression fails
before this repair and passes after it; the full Python suite passes
488 tests with 3 existing skips. Real cross-platform inference must still
prove that this repair resolves the observed runtime failures.

ARM runtime 35559727899 (a03aab19) still receives runner shutdown during
untimed alignment. The watchdog now locates execution inside Whisper's
encoder during desktop timing recovery. Available memory before untimed
alignment is 5149974528 bytes; native reference release alone is insufficient.
A second model-free regression checks cyclic model objects across desktop
steps and after construction failure, with automatic GC disabled. Both
cases fail before explicit cleanup. Desktop jobs now clear pipeline and
backend argument references and collect cycles after each step and in the
final cleanup path. Both regressions and the full Python suite pass locally;
real inference with this additional repair remains a CI gate.

Intel macOS run 35552384706 (e5272755) completes the entire native job:
all real pipeline checks, the GUI morphology-to-compare flow, and both
cold/warm native launches pass. Untimed alignment takes 629769 ms; cold
sidecar bootstrap takes 508165 ms and warm bootstrap 1055 ms. The macOS
native test uses the documented ad-hoc-signed QA app with embedded driver.
This is evidence for that revision, not a pass for subsequent changes.

Revision 7c7549fb replaces the Windows driver's window-close command with
CloseMainWindow on the exact installed executable and requires actual host
exit within ten seconds before checking daemon shutdown and warm relaunch.
The older driver operation did not establish native-host termination.
Actual execution of this stronger Windows gate remains pending.

Apple Silicon runtime 35559727899 (a03aab19) passes cold/warm bootstrap
(157773/924 ms), comparison and input smash, but transcription remains in
running state at the 30-minute deadline. The harness stops the daemon and
does not proceed to other models. Its tail contains no inference traceback.
Windows on the same revision loses its status socket during transcription;
its diagnostics contain no explanatory crash event. Extend the existing
CI-only diagnostic flag to model constructors and pipeline.run, identifying
each phase and dumping stacks every 60 seconds. Four model-free cases check
opt-in behavior and watchdog cancellation on success and exceptions. They
pass through the repository pytest recipe; runtime deadlines stay unchanged.

Runtime 35562533393 (937ca54c) proves that cyclic-model cleanup is helpful
but insufficient: Linux x64 reports 9257877504 free bytes before untimed
alignment, versus roughly 5.2 GB before cleanup, yet its runner still shuts
down during that stage. Windows passes transcription (WER 0.2222), timed
alignment and 259 smash inputs, then loses its daemon during Whisper timing
recovery. Desktop alignment now runs its UTR batch before constructing FA,
stages intermediate CHAT privately, releases UTR and collects cycles, then
loads FA. Both passes retain original source IDs for media lookup. Recovery
does not emit the final alignment completion event or publish intermediate
outputs. Model-free regressions cover release before FA construction and
recovery failure preserving the source and skipping FA. Real-model results
for this sequencing change remain required; memory snapshots alone do not
prove the cause of the runner shutdowns.

Windows native run 35562533393 (937ca54c) passes the stronger installed-MSI
gate: cold launch 283735 ms with 68 bootstrap progress updates, correct
comparison output, actual WM_CLOSE host exit and daemon shutdown, warm
launch 2563 ms, and a second clean host/daemon shutdown. Apple Silicon
native run 35559727899 (a03aab19) also passes cold/warm launch and both
shutdown checks with the QA app (189155/4928 ms, 60 progress updates).
These passes do not imply that their real-model runtime failures passed.

Linux ARM run 35566034597 (78189a17) passes transcription in 203625 ms and
timed alignment in 12058 ms, then receives runner shutdown/exit 143 during
the separate UTR Whisper encoder pass. Its system free-memory figure is
8985124864 bytes before UTR; that figure does not distinguish resident
models from reclaimable file cache. Add process VmRSS/VmHWM diagnostics
around collection and Linux malloc_trim to distinguish allocator retention
from live allocations. The trim hook returns unused glibc arena pages
between models; unsupported allocators retain ordinary collection. This
does not change model size, inference precision, or the correctness gates.
CI must still establish whether it resolves the failure.
