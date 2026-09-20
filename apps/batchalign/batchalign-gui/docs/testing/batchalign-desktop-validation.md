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
- Current local frontend: 13 unit/property tests and 10 Chromium GUI tests pass
  (all six individual steps and a four-step chain; GUI boundary is mocked).
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
- Native daemon startup can leak a child on timeout; exited daemon does not
  reset its spawn latch. Cache invalidation deletes every project install and
  marker writes tag every version, instead of targeting this bundle's install.
- Existing gui.spec.ts remains stale: 60-second bootstrap budget, old overlay
  selectors, and tolerated recipe/capability errors. Replace it with real
  pipeline/output assertions using the new orchestration endpoint.
- Native SSE pump cancellation/removal races and relay request timeouts still
  need focused tests; HTTP reconnects currently fail the batch on first error.
- Re-run behavior: BATCH_STARTED replaces discovery rows with selected inputs;
  changing pipeline type after a run may require re-scanning the folder.
- Settings still need complete mapping: memory/adaptive-worker controls,
  stored Rev.AI key, and skip-code-switching semantics. Global/local models
  must honor force-CPU even where constructors lack a device parameter.
- In-place .chat suffix preservation has a regression test; only media inputs
  switch to the .cha output suffix.
- Native comparison CSV file labels previously appended .cha to absolute CHAT
  paths (yielding .cha.cha); fixed with a native integration assertion.
- CI provider-secret listing was empty. Need live-provider credentials/test
  strategy; do not count fake services as provider correctness. There is ample
  independent work before this can constitute a blocker.

Do not mark the goal complete until all required platform/pipeline gates have
passing evidence. Existing tests and new configuration alone are insufficient.
