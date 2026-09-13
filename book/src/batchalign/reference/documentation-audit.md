# Batchalign documentation audit

Audit baseline: `fbaee727d9649f8d4bf1592433fb71f7acce7b12` (0.10.1 release source).
Scope: every existing Markdown page under `book/src/batchalign/`, plus the shared
runtime pages reached from Batchalign navigation. Supporting Chatter/CLAN/editor
navigation was classified by Diátaxis; those products' implementations were not
re-audited as part of the Batchalign runtime cleanup.

Current CLI facts were checked against the Typer registry and command modules;
pipeline, queue, and cache claims against the Rust engine; model/rendering
ownership against Python backends; build and release instructions against the
`just` recipes and CI workflows. Command-reference options were extracted from
source and checked against the authoritative CLI help. Historical model results
were not rerun or promoted to current accuracy guarantees.

The quick start retains its original command-window walkthrough and task order;
changes there remove obsolete commands/options and correct cache/model claims.
Consolidated pages retain their URLs as pointers. Historical research remains
available through fixed-revision links.

| Page | Disposition | Current destination or evidence |
|---|---|---|
| [architecture/algorithm-visualizations.md](../architecture/algorithm-visualizations.md) | Consolidated | [Current page](../user-guide/review-tiers-guide.md); The former dashboard visualization endpoints are not part of the current service. |
| [architecture/align-throughput.md](../architecture/align-throughput.md) | Consolidated | [Current page](../user-guide/performance.md); Worker pre-scaling and server admission heuristics are not the current CLI controls. |
| [architecture/asr-token-pipeline.md](../architecture/asr-token-pipeline.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [architecture/cache-override-guide.md](../architecture/cache-override-guide.md) | Consolidated | [Current page](../user-guide/cache-management.md); The current CLI does not expose --override-media-cache. Python callers choose a CacheSpec policy. |
| [architecture/chat-parsing.md](../architecture/chat-parsing.md) | Consolidated | [Current page](../architecture/command-lifecycles.md); The former server/PyO3 ownership map did not match the in-process engine. |
| [architecture/command-contracts.md](../architecture/command-contracts.md) | Consolidated | [Current page](../architecture/command-lifecycles.md); The former validity-level table referred to the retired command orchestrators; current preconditions belong to each typed runner. |
| [architecture/command-flowcharts.md](../architecture/command-flowcharts.md) | Consolidated | [Current page](../architecture/command-lifecycles.md); The former flag-routing charts described commands and server dispatch paths that are no longer registered. |
| [architecture/command-lifecycles.md](../architecture/command-lifecycles.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [architecture/incremental-processing.md](../architecture/incremental-processing.md) | Consolidated | [Current page](../user-guide/caching.md); Current reuse comes from typed backend result keys; the old server diff/orchestrator description is not a current CLI contract. |
| [architecture/job-state-machine.md](../architecture/job-state-machine.md) | Consolidated | [Current page](../architecture/server-architecture.md); The former persistent Rust job state machine does not describe the FastAPI in-memory registry. |
| [architecture/morphotag-invariants.md](../architecture/morphotag-invariants.md) | Consolidated | [Current page](morphosyntax.md); The former MorOutcome and worker reconciliation description does not identify the current typed injection path. |
| [architecture/number-expansion.md](../architecture/number-expansion.md) | Consolidated | [Current page](../architecture/asr-token-pipeline.md); The earlier page mixed language/format background with implementation paths, flags, or behavior from a previous runtime. |
| [architecture/observability.md](../architecture/observability.md) | Consolidated | [Current page](../user-guide/progress-and-feedback.md); The old SQLite/Temporal job observability model is not implemented by the current CLI. |
| [architecture/overlap-encoding.md](../architecture/overlap-encoding.md) | Consolidated | [Current page](forced-alignment.md); The earlier page mixed language/format background with implementation paths, flags, or behavior from a previous runtime. |
| [architecture/path-provenance.md](../architecture/path-provenance.md) | Consolidated | [Current page](../architecture/server-architecture.md); The old client/server path newtypes and remote media mappings are not the local CLI path contract. |
| [architecture/pipeline-decisions.md](../architecture/pipeline-decisions.md) | Consolidated | [Current page](../user-guide/review-tiers-guide.md); Existing decision types alone do not establish that all current runners emit the former review tiers and CLI controls. |
| [architecture/preprocessing-postprocessing.md](../architecture/preprocessing-postprocessing.md) | Consolidated | [Current page](../architecture/command-lifecycles.md); The former claim that all linguistic processing lived in Rust was incorrect: Stanza token processing and rendering also live in Python. |
| [architecture/progress-reporting.md](../architecture/progress-reporting.md) | Consolidated | [Current page](../user-guide/progress-and-feedback.md); Current CLI progress uses Rust events and Python callbacks rather than the former server FileStatus stream. |
| [architecture/provenance.md](../architecture/provenance.md) | Consolidated | [Current page](../user-guide/provenance.md); The former bracketed ba3 format and server-owned injection sites do not match current stamping. |
| [architecture/replacements-handling.md](../architecture/replacements-handling.md) | Consolidated | [Current page](morphosyntax.md); The earlier page mixed language/format background with implementation paths, flags, or behavior from a previous runtime. |
| [architecture/server-architecture.md](../architecture/server-architecture.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [architecture/server-model-loading.md](../architecture/server-model-loading.md) | Consolidated | [Current page](../user-guide/performance.md); The former worker profiles and warmup configuration do not configure the current backends. |
| [architecture/stanza-capability-registry.md](../architecture/stanza-capability-registry.md) | Consolidated | [Current page](morphosyntax.md); The current Stanza backend resolves language configurations directly; the former worker capability exchange is obsolete. |
| [architecture/stanza-defect-mitigation-map.md](../architecture/stanza-defect-mitigation-map.md) | Consolidated | [Current page](morphosyntax.md); The former patch-point table cited deleted worker/inference modules; current tokenizer and renderer ownership is documented here. |
| [architecture/test-server-lifecycle.md](../architecture/test-server-lifecycle.md) | Consolidated | [Current page](../developer/testing.md); Current product tests do not use the former shared Rust server fixture lifecycle. |
| [architecture/time-transparency.md](../architecture/time-transparency.md) | Consolidated | [Current page](../user-guide/progress-and-feedback.md); The UX goal of visible progress remains useful, but the worker progress_v2 mechanism in the former page is obsolete. |
| [architecture/type-driven-design.md](../architecture/type-driven-design.md) | Consolidated | [Current page](../architecture/command-lifecycles.md); The former examples mixed current core types with removed server and worker-protocol types. |
| [architecture/worker-failure-classification.md](../architecture/worker-failure-classification.md) | Consolidated | [Current page](../developer/tracing-and-debugging.md); The retired worker JSON protocol and server retry classifier do not describe in-process backend failures. |
| [decisions/lenient-parsing.md](../decisions/lenient-parsing.md) | Historical record | [Current page](historical-notes.md); An earlier parser-policy decision; prior runtime/version evidence is not a current guarantee. |
| [decisions/models-training-runtime-adr.md](../decisions/models-training-runtime-adr.md) | Historical record | [Current page](historical-notes.md); An earlier model-training/runtime decision; prior runtime/version evidence is not a current guarantee. |
| [decisions/release-state-machine.md](../decisions/release-state-machine.md) | Historical record | [Current page](historical-notes.md); An earlier release-state proposal; prior runtime/version evidence is not a current guarantee. |
| [decisions/trait-based-dispatch.md](../decisions/trait-based-dispatch.md) | Historical record | [Current page](historical-notes.md); An earlier algorithm-dispatch decision; prior runtime/version evidence is not a current guarantee. |
| [developer/adding-commands.md](../developer/adding-commands.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [developer/adding-engines.md](../developer/adding-engines.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [developer/adding-language-support.md](../developer/adding-language-support.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [developer/api-stability.md](../developer/api-stability.md) | Consolidated | [Current page](../user-guide/python-api.md); The previous assertion that no Python API exists was false. The package exposes pipelines, recipes, inputs, and backend interfaces. |
| [developer/apple-mps-workarounds.md](../developer/apple-mps-workarounds.md) | Consolidated | [Current page](../user-guide/performance.md); The blanket MPS prohibition is obsolete: applicable commands now have an explicit --allow-mps option. |
| [developer/arena-allocators.md](../developer/arena-allocators.md) | Historical record | [Current page](historical-notes.md); An earlier allocator evaluation; prior runtime/version evidence is not a current guarantee. |
| [developer/backchannel-aware-alignment.md](../developer/backchannel-aware-alignment.md) | Consolidated | [Current page](forced-alignment.md); The old --utr-strategy/--utr-fuzzy CLI controls are not registered; the UTR implementation has its own current strategy selection. |
| [developer/building.md](../developer/building.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [developer/chat-validation-failures.md](../developer/chat-validation-failures.md) | Consolidated | [Current page](chat-format.md); The earlier page mixed language/format background with implementation paths, flags, or behavior from a previous runtime. |
| [developer/commands/align.md](../developer/commands/align.md) | Consolidated | [Current page](forced-alignment.md); The earlier page mixed language/format background with implementation paths, flags, or behavior from a previous runtime. |
| [developer/commands/benchmark.md](../developer/commands/benchmark.md) | Consolidated | [Current page](../user-guide/commands/benchmark.md); The former benchmark orchestrator is not a current command entrypoint. |
| [developer/commands/compare.md](../developer/commands/compare.md) | Consolidated | [Current page](../user-guide/commands/compare.md); The earlier page mixed language/format background with implementation paths, flags, or behavior from a previous runtime. |
| [developer/commands/coref.md](../developer/commands/coref.md) | Consolidated | [Current page](../user-guide/commands/coref.md); The earlier page mixed language/format background with implementation paths, flags, or behavior from a previous runtime. |
| [developer/commands/morphotag.md](../developer/commands/morphotag.md) | Consolidated | [Current page](morphosyntax.md); The earlier page mixed language/format background with implementation paths, flags, or behavior from a previous runtime. |
| [developer/commands/transcribe.md](../developer/commands/transcribe.md) | Consolidated | [Current page](../user-guide/commands/transcribe.md); The earlier page mixed language/format background with implementation paths, flags, or behavior from a previous runtime. |
| [developer/commands/translate.md](../developer/commands/translate.md) | Consolidated | [Current page](../user-guide/commands/translate.md); The earlier page mixed language/format background with implementation paths, flags, or behavior from a previous runtime. |
| [developer/commands/utseg.md](../developer/commands/utseg.md) | Consolidated | [Current page](../user-guide/commands/utseg.md); The earlier page mixed language/format background with implementation paths, flags, or behavior from a previous runtime. |
| [developer/debugging-infrastructure.md](../developer/debugging-infrastructure.md) | Consolidated | [Current page](../developer/tracing-and-debugging.md); The current CLI does not promise the former always-on server failure dumps. |
| [developer/decision-provenance.md](../developer/decision-provenance.md) | Consolidated | [Current page](../user-guide/review-tiers-guide.md); The former blanket review-tier emission contract is not exposed by the current CLI. |
| [developer/gra-correctness-guarantee.md](../developer/gra-correctness-guarantee.md) | Consolidated | [Current page](morphosyntax.md); The former guarantee cited a different generator; the current renderer and typed alignment checks are documented here. |
| [developer/host-facts.md](../developer/host-facts.md) | Consolidated | [Current page](../user-guide/performance.md); The former host-facts/bootstrap coordinator is not part of this CLI execution path. |
| [developer/http-body-limits.md](../developer/http-body-limits.md) | Consolidated | [Current page](../architecture/server-architecture.md); The former Rust route-body configuration is not the current FastAPI service contract; inspect its OpenAPI schema and route implementation. |
| [developer/investigation-probe-harnesses.md](../developer/investigation-probe-harnesses.md) | Consolidated | [Current page](../developer/testing.md); The former probe runner commands and server setup are not current test entrypoints. |
| [developer/ipc-type-sync.md](../developer/ipc-type-sync.md) | Consolidated | [Current page](../developer/adding-engines.md); Protocol schemas are generated from the core proto types through Bazel, not the removed batchalign-types worker_v2 tree. |
| [developer/landing-status.md](../developer/landing-status.md) | Consolidated | [Current page](../developer/rust-workspace-map.md); The former migration landing checklist is no longer a source map for the current implementation. |
| [developer/maturin-pyo3-surface.md](../developer/maturin-pyo3-surface.md) | Consolidated | [Current page](../developer/rust-workspace-map.md); The old extension-module name, crate layout, and editable-install instructions were obsolete. |
| [developer/memory-safety.md](../developer/memory-safety.md) | Consolidated | [Current page](../user-guide/performance.md); The current engine bounds queues and active files; it does not enforce the former host-wide worker-startup memory leases. |
| [developer/model-downloads-and-caching.md](../developer/model-downloads-and-caching.md) | Consolidated | [Current page](../user-guide/caching.md); The worker-loader inventory and audio-only SQLite cache claims were obsolete. |
| [developer/non-english-workarounds.md](../developer/non-english-workarounds.md) | Consolidated | [Current page](language-handling.md); The earlier page mixed language/format background with implementation paths, flags, or behavior from a previous runtime. |
| [developer/plugins.md](../developer/plugins.md) | Consolidated | [Current page](../developer/adding-engines.md); The current extension point is the backend interface and recipe composition, not the former worker capability registry. |
| [developer/python-versioning.md](../developer/python-versioning.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [developer/regression-fixtures.md](../developer/regression-fixtures.md) | Consolidated | [Current page](../developer/testing.md); The former harness paths have changed; use the current product tests and representative CLI fixtures. |
| [developer/release-checklist.md](../developer/release-checklist.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [developer/release-contract.md](../developer/release-contract.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [developer/reliability-program.md](../developer/reliability-program.md) | Consolidated | [Current page](../developer/testing.md); The former scorecard mixed proposed fleet procedures with claims about shipped tests. |
| [developer/rust-cli-and-server.md](../developer/rust-cli-and-server.md) | Consolidated | [Current page](../architecture/command-lifecycles.md); The current CLI and HTTP service are Python entrypoints around the Rust pipeline. |
| [developer/rust-contributor-onboarding.md](../developer/rust-contributor-onboarding.md) | Consolidated | [Current page](../developer/building.md); Current contributor commands go through the repository just recipes and Bazel targets. |
| [developer/rust-core.md](../developer/rust-core.md) | Consolidated | [Current page](../developer/rust-workspace-map.md); The extension is batchalign._core and its runtime lives in batchalign-engine, not the retired batchalign-pyo3 layout. |
| [developer/rust-workspace-map.md](../developer/rust-workspace-map.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [developer/tauri-react-dashboard.md](../developer/tauri-react-dashboard.md) | Consolidated | [Current page](../user-guide/desktop-app.md); The old cli-web-statuspage/dashboard-desktop paths and Rust server setup have been replaced. |
| [developer/terminator-architecture.md](../developer/terminator-architecture.md) | Consolidated | [Current page](chat-format.md); The earlier page mixed language/format background with implementation paths, flags, or behavior from a previous runtime. |
| [developer/testing-turmoil.md](../developer/testing-turmoil.md) | Consolidated | [Current page](../developer/testing.md); The former network-simulation harness is not a current Batchalign test recipe. |
| [developer/testing.md](../developer/testing.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [developer/tracing-and-debugging.md](../developer/tracing-and-debugging.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [developer/upstream-defect-policy.md](../developer/upstream-defect-policy.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [developer/worker-protocol-v2.md](../developer/worker-protocol-v2.md) | Consolidated | [Current page](../developer/adding-engines.md); Backend calls cross the in-process typed engine boundary; the old worker_v2 transport is not the current interface. |
| [developer/workflow-contributor-guide.md](../developer/workflow-contributor-guide.md) | Consolidated | [Current page](../developer/adding-commands.md); ReleasedCommand and Rust command-family registration no longer own the CLI surface. |
| [introduction.md](../introduction.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [migration/algorithms-and-language.md](../migration/algorithms-and-language.md) | Historical record | [Current page](historical-notes.md); A comparison of earlier BA2 and Rust-server algorithms; prior runtime/version evidence is not a current guarantee. |
| [migration/ba2-architecture-reference.md](../migration/ba2-architecture-reference.md) | Historical record | [Current page](historical-notes.md); The BA2 implementation baseline; prior runtime/version evidence is not a current guarantee. |
| [migration/ba2-cli-reference.md](../migration/ba2-cli-reference.md) | Historical record | [Current page](historical-notes.md); The BA2 command-line baseline; prior runtime/version evidence is not a current guarantee. |
| [migration/ba2-compare-migration.md](../migration/ba2-compare-migration.md) | Consolidated | [Current page](../user-guide/commands/compare.md); The earlier page mixed language/format background with implementation paths, flags, or behavior from a previous runtime. |
| [migration/debugging-and-tracing.md](../migration/debugging-and-tracing.md) | Consolidated | [Current page](../developer/tracing-and-debugging.md); The earlier page mixed language/format background with implementation paths, flags, or behavior from a previous runtime. |
| [migration/developer-migration.md](../migration/developer-migration.md) | Consolidated | [Current page](../developer/rust-workspace-map.md); The earlier page mixed language/format background with implementation paths, flags, or behavior from a previous runtime. |
| [migration/index.md](../migration/index.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [migration/persistent-state.md](../migration/persistent-state.md) | Consolidated | [Current page](../user-guide/caching.md); The earlier page mixed language/format background with implementation paths, flags, or behavior from a previous runtime. |
| [migration/python-to-rust-rationale.md](../migration/python-to-rust-rationale.md) | Historical record | [Current page](historical-notes.md); The rationale for an earlier ownership migration; prior runtime/version evidence is not a current guarantee. |
| [migration/user-migration.md](../migration/user-migration.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [reference/benchmarks.md](benchmarks.md) | Consolidated | [Current page](../user-guide/commands/benchmark.md); The former benchmark command is not registered in the current CLI. |
| [reference/chat-format.md](chat-format.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [reference/chat-options.md](chat-options.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [reference/chinese-word-segmentation.md](chinese-word-segmentation.md) | Consolidated | [Current page](morphosyntax.md); The earlier page mixed language/format background with implementation paths, flags, or behavior from a previous runtime. |
| [reference/command-io.md](command-io.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [reference/cross-repo-dependency.md](cross-repo-dependency.md) | Consolidated | [Current page](../developer/rust-workspace-map.md); Use the current workspace dependency declarations rather than the former sibling-checkout contract. |
| [reference/english-transcribe-corrections.md](english-transcribe-corrections.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [reference/filesystem-paths.md](filesystem-paths.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [reference/forced-alignment.md](forced-alignment.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [reference/gra-format.md](gra-format.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [reference/hebrew-morphosyntax.md](hebrew-morphosyntax.md) | Consolidated | [Current page](languages/hebrew.md); The earlier page mixed language/format background with implementation paths, flags, or behavior from a previous runtime. |
| [reference/japanese-morphosyntax.md](japanese-morphosyntax.md) | Consolidated | [Current page](languages/japanese.md); The earlier page mixed language/format background with implementation paths, flags, or behavior from a previous runtime. |
| [reference/l2-handling.md](l2-handling.md) | Consolidated | [Current page](language-handling.md); The earlier page mixed language/format background with implementation paths, flags, or behavior from a previous runtime. |
| [reference/l2-morphotag-literature.md](l2-morphotag-literature.md) | Historical record | [Current page](historical-notes.md); Literature considered for the earlier code-switching design; prior runtime/version evidence is not a current guarantee. |
| [reference/l2-morphotag-status.md](l2-morphotag-status.md) | Historical record | [Current page](historical-notes.md); An earlier implementation-status and accuracy report; prior runtime/version evidence is not a current guarantee. |
| [reference/l2-morphotag.md](l2-morphotag.md) | Historical record | [Current page](historical-notes.md); Per-word code-switching design and its earlier evaluation; prior runtime/version evidence is not a current guarantee. |
| [reference/language-code-resolution.md](language-code-resolution.md) | Consolidated | [Current page](language-handling.md); The earlier page mixed language/format background with implementation paths, flags, or behavior from a previous runtime. |
| [reference/language-handling.md](language-handling.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [reference/language-specific-processing.md](language-specific-processing.md) | Consolidated | [Current page](language-handling.md); The earlier page mixed language/format background with implementation paths, flags, or behavior from a previous runtime. |
| [reference/languages/cantonese.md](languages/cantonese.md) | Revised | Current routing/source notes; older model probes linked at a fixed revision without revalidation claims. |
| [reference/languages/dutch.md](languages/dutch.md) | Revised | Current routing/source notes; older model probes linked at a fixed revision without revalidation claims. |
| [reference/languages/french.md](languages/french.md) | Revised | Current routing/source notes; older model probes linked at a fixed revision without revalidation claims. |
| [reference/languages/hebrew.md](languages/hebrew.md) | Revised | Current routing/source notes; older model probes linked at a fixed revision without revalidation claims. |
| [reference/languages/italian.md](languages/italian.md) | Revised | Current routing/source notes; older model probes linked at a fixed revision without revalidation claims. |
| [reference/languages/japanese.md](languages/japanese.md) | Revised | Current routing/source notes; older model probes linked at a fixed revision without revalidation claims. |
| [reference/languages/malayalam.md](languages/malayalam.md) | Revised | Current routing/source notes; older model probes linked at a fixed revision without revalidation claims. |
| [reference/languages/mandarin.md](languages/mandarin.md) | Revised | Current routing/source notes; older model probes linked at a fixed revision without revalidation claims. |
| [reference/languages/overview.md](languages/overview.md) | Revised | Current routing/source notes; older model probes linked at a fixed revision without revalidation claims. |
| [reference/languages/portuguese.md](languages/portuguese.md) | Revised | Current routing/source notes; older model probes linked at a fixed revision without revalidation claims. |
| [reference/media-conversion.md](media-conversion.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [reference/morphosyntax.md](morphosyntax.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [reference/morphotag-retokenization.md](morphotag-retokenization.md) | Consolidated | [Current page](morphosyntax.md); The old --keeptokens flag and worker-side module paths are obsolete; current modes use --retokenize/--no-retokenize. |
| [reference/multilingual.md](multilingual.md) | Consolidated | [Current page](language-handling.md); The earlier page mixed language/format background with implementation paths, flags, or behavior from a previous runtime. |
| [reference/mwt-handling.md](mwt-handling.md) | Consolidated | [Current page](morphosyntax.md); The earlier page mixed language/format background with implementation paths, flags, or behavior from a previous runtime. |
| [reference/nlp-engine-text-input.md](nlp-engine-text-input.md) | Consolidated | [Current page](morphosyntax.md); The earlier page mixed language/format background with implementation paths, flags, or behavior from a previous runtime. |
| [reference/number-expansion.md](number-expansion.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [reference/overlap-markers.md](overlap-markers.md) | Consolidated | [Current page](forced-alignment.md); The earlier page mixed language/format background with implementation paths, flags, or behavior from a previous runtime. |
| [reference/platform-support.md](platform-support.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [reference/pos-hints.md](pos-hints.md) | Consolidated | [Current page](morphosyntax.md); The earlier page mixed language/format background with implementation paths, flags, or behavior from a previous runtime. |
| [reference/retokenization-overview.md](retokenization-overview.md) | Consolidated | [Current page](morphosyntax.md); The earlier page mixed language/format background with implementation paths, flags, or behavior from a previous runtime. |
| [reference/retrace-detection.md](retrace-detection.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [reference/revai-language-quality-strategy.md](revai-language-quality-strategy.md) | Historical record | [Current page](historical-notes.md); A proposed Rev.AI quality-assessment strategy; prior runtime/version evidence is not a current guarantee. |
| [reference/stanza-limitations.md](stanza-limitations.md) | Historical record | [Current page](historical-notes.md); Version-specific model observations and former mitigation claims; prior runtime/version evidence is not a current guarantee. |
| [reference/textgrid.md](textgrid.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [reference/utterance-segmentation.md](utterance-segmentation.md) | Consolidated | [Current page](../user-guide/commands/utseg.md); The earlier page mixed language/format background with implementation paths, flags, or behavior from a previous runtime. |
| [reference/whisper-asr.md](whisper-asr.md) | Consolidated | [Current page](../user-guide/commands/transcribe.md); The earlier page mixed language/format background with implementation paths, flags, or behavior from a previous runtime. |
| [reference/wor-tier.md](wor-tier.md) | Consolidated | [Current page](forced-alignment.md); The earlier page mixed language/format background with implementation paths, flags, or behavior from a previous runtime. |
| [user-guide/caching.md](../user-guide/caching.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [user-guide/cantonese-processing.md](../user-guide/cantonese-processing.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [user-guide/cli-reference.md](../user-guide/cli-reference.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [user-guide/commands/align.md](../user-guide/commands/align.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [user-guide/commands/benchmark.md](../user-guide/commands/benchmark.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [user-guide/commands/compare.md](../user-guide/commands/compare.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [user-guide/commands/coref.md](../user-guide/commands/coref.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [user-guide/commands/eval.md](../user-guide/commands/eval.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [user-guide/commands/morphotag.md](../user-guide/commands/morphotag.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [user-guide/commands/transcribe.md](../user-guide/commands/transcribe.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [user-guide/commands/translate.md](../user-guide/commands/translate.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [user-guide/commands/utseg.md](../user-guide/commands/utseg.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [user-guide/dashboard.md](../user-guide/dashboard.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [user-guide/desktop-app.md](../user-guide/desktop-app.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [user-guide/doctor.md](../user-guide/doctor.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [user-guide/installation.md](../user-guide/installation.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [user-guide/model-downloads.md](../user-guide/model-downloads.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [user-guide/performance.md](../user-guide/performance.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [user-guide/progress-and-feedback.md](../user-guide/progress-and-feedback.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [user-guide/provenance.md](../user-guide/provenance.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [user-guide/python-api.md](../user-guide/python-api.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [user-guide/quick-start.md](../user-guide/quick-start.md) | Revised | Preserved tutorial structure; corrected obsolete syntax and cache/model claims. |
| [user-guide/rev-ai.md](../user-guide/rev-ai.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [user-guide/review-tiers-guide.md](../user-guide/review-tiers-guide.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [user-guide/server-mode.md](../user-guide/server-mode.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [user-guide/server-setup.md](../user-guide/server-setup.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [user-guide/troubleshooting.md](../user-guide/troubleshooting.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
| [user-guide/worker-tuning.md](../user-guide/worker-tuning.md) | Revised | Rewritten against current owning CLI, core/engine, backend, or build sources; obsolete claims removed. |
