# Desktop cleanroom validation

Completion requires an installed desktop bundle, after macOS quarantine/signing
bypass where necessary, to start and execute every supported GUI pipeline
correctly. A successful build, health check, accepted job, or mocked backend is
not evidence of pipeline correctness. Preserve the existing interface.

## Required evidence

- Native packages: macOS arm64 and x86_64, Linux x86_64, Windows x86_64.
- Fresh install with isolated application/PyApp/model/config caches; visible
  bootstrap progress, capabilities handshake, warm relaunch, failure diagnosis.
- All six GUI steps (transcribe, diarize, align, morphotag, translate, compare),
  their selectable backends and supported compositions, checked against actual
  output artifacts. Verify output directory, in-place mode, nested paths,
  Unicode/spaces, progress, error reporting, and restart/retry behavior.
- GUI unit tests, property tests, and seeded randomized interaction/event tests.
- Native IPC, HTTP relay and SSE tests in installed packages, beyond browser
  tests that stub the Tauri boundary.
- CI artifacts retain logs, test results and failure screenshots/traces. Run
  heavy builds/model environments on GitHub runners, not this laptop.

## Current evidence (2026-09-20)

- Clean starting worktree at 46be801. Published build run 34803282092 succeeds
  for macOS arm64/x86_64 and Linux x86_64. It does not exercise installation,
  native startup, or pipeline execution. Windows is explicitly excluded.
- Startup regression tests reproduced warm-launch hang and lost cold-start
  progress/failure subscriptions under React StrictMode. Fixed listener
  ownership and consumption of ensure_daemon's returned port. Chromium: three
  regressions pass. Production frontend build passes.
- Six GUI unit/property tests pass: 100 seeded remount/readiness sequences,
  500 tab-action sequences, cleanup during pending registration, stale
  capabilities after failure, warm readiness. Properties found and fixed
  invalid active tabs and capabilities surviving daemon failure/restart.
- WebKit is not installed locally; the new GUI CI matrix installs each browser
  on macOS arm64/x86_64, Linux, and Windows. Configuration is not run evidence.
- Local sidecar rebuild was deliberately interrupted to move heavy work to CI.
- Published macOS arm64 bundle download requested in
  /tmp/batchalign-cleanroom-34803282092 (check process/download before reuse).

## Confirmed remaining defects / investigation

- useStartBatch submits only pipeline[0]; subsequent selected steps never run.
- inPlace/outputPath and global worker/device options are not sent or applied.
- API recipe worker serializes BAValue outcomes as progress-like JSON; it does
  not write results. Desktop execution needs real output handling.
- AlignPanel stores `aligner`, but request builder reads `engine` and defaults
  to WhisperXFaBackend. File filtering selects both media and CHAT for align,
  while CLI alignment processes CHAT with associated media.
- Compare filtering incorrectly pairs audio and CHAT; CLI comparison requires
  FILE.gold.cha or template.gold.cha and excludes golds as primary inputs.
- GUI constructs input paths using filename, losing nested source_id paths,
  and omits explicit source_id needed to route progress to file rows.
- Native SSE relay sets a zero-duration reqwest timeout; investigate and test.
- Native daemon startup can leak a child on timeout; exited daemon does not
  reset spawn latch. Cache invalidation traverses/deletes every project install
  and marker writes tag every version, rather than only this bundle's install.
- Existing gui.spec.ts has a wrong repository-root depth, 60-second bootstrap
  budget, stale overlay selectors, and tolerates recipe/capability errors.
- CI has no provider secrets listed. Exercise real local models and determine
  how external-service pipelines will be verified; do not count mocks as real
  provider correctness.

Do not mark the goal complete until every required platform/pipeline gate has
actual passing evidence. Keep resource-intensive execution on CI.
