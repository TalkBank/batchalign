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
