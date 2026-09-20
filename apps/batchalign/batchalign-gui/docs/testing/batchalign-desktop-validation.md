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

Do not mark the goal complete until all required platform/pipeline gates have
passing evidence. Existing tests and new configuration alone are insufficient.
