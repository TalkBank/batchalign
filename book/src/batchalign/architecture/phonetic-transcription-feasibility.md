# Phonetic transcription feasibility

Investigation date: 2026-09-20. Proposal only; no command or backend has been
implemented and no model inference has been benchmarked.

Adding acoustic phonetic transcription is feasible within the current pipeline.
Use Batchalign's existing normalize–DP–project pattern to map recognized phones
to CHAT phonological positions. Task registration and tier writing also have
established patterns. The remaining uncertainties are pronunciation conversion,
ownership of unmatched phones, and accuracy on TalkBank recordings.

## Model fit

[PhoneticXeus](https://huggingface.co/changelinglab/PhoneticXeus) accepts mono
16 kHz audio and produces IPA. Its public `transcribe()` returns joined IPA and
slash-delimited phone tokens; `forward()` exposes frame-level CTC logits. It does
not directly return CHAT word boundaries or phone timestamps. Preserve token
identities rather than splitting joined IPA into Unicode characters: one phone
may contain multiple code points.

The model card lists Apache-2.0, approximately 0.6B parameters, and F32 weights
(roughly 2.4 GB for weights alone, estimated; runtime memory is higher). The
documented dependencies substantially overlap the existing Torch/Transformers
stack. Dependency compatibility, CPU speed, CUDA memory, and Apple MPS behavior
still require measurement. Start with an optional dependency extra and CPU/CUDA
support; do not promise MPS support without a smoke test.

The [paper](https://arxiv.org/abs/2603.29042) reports 17.7% multilingual and 10.6%
accented-English phone-feature error rates. These are feature-based metrics,
not percentages of incorrectly recognized phones. They do not establish accuracy
on child speech, disorders, overlap, or noisy conversational TalkBank audio.

The [upstream README](https://github.com/changelinglab/PhoneticXeus) reports a
2026-09-20 correction enabling self-conditioning during inference. Pin a tested
revision containing that fix. The HF revision observed during this investigation
was `3a8d860fa68f8936ceb4196651221215bab9dae4`.
The [loader](https://huggingface.co/changelinglab/PhoneticXeus/blob/main/modeling_phoneticxeus.py)
internally calls `snapshot_download()` without forwarding a revision. Therefore,
passing only `revision=` to `AutoModel.from_pretrained()` is insufficient to pin
all code. Download the required code, configuration, and weights at a specific
revision and load that local snapshot. Its custom code and global `pxeus` imports
also need review before supporting multiple revisions in one process.

## CHAT contract and alignment

The resolved `talkbank-model` 0.16.0 dependency already provides `PhoTier::new_pho`,
`PhoItem::Word`, and `PhoItem::Group`, with serialization and alignment validation.
No new CHAT syntax is needed. `%pho` describes observed pronunciation; canonical
pronunciation belongs in `%mod` and is a separate potential task.

The [alignment contract](../../architecture/alignment.md) counts phonological
positions, not simply orthographic whitespace tokens. Retraces, pauses, fillers,
fragments, nonwords, untranscribed material, replacements, and phonological groups
require the `TierDomain::Pho` rules. `%wor` has different membership rules, so its
timings cannot be zipped directly with `%pho` items.

Recommended approach, following the user's proposed BA alignment pattern:

1. Recognize IPA from audio, preserving each original phone token and its index.
2. Convert the recognized phones to comparison symbols (ARPAbet for an initial
   English path), retaining comparison-symbol-to-original-phone ownership.
3. Read words from CHAT, or obtain them from normal ASR for raw media. Convert
   them to the same comparison alphabet, retaining each symbol's CHAT unit and
   utterance identity. Pronunciation lookup/G2P needs explicit handling of
   alternatives, out-of-vocabulary words, and stress normalization.
4. DP-align the two flattened comparison sequences. Project reference word/unit
   boundaries back onto the recognized phone sequence using the ownership maps.
5. Write the original recognized IPA, grouped by those projected boundaries,
   into typed `%pho` items. Canonical phones guide grouping; they never replace
   the acoustic transcription.

This does **not** require word-level FA or phone timestamps. Existing utterance
windows or ASR segmentation can bound recognition and DP work; UTR is optional
for recovering missing windows. Bounded chunks need overlap/deduplication and
monotonic projection when they do not coincide with CHAT utterances. A direct
IPA-to-comparison mapping avoids an unnecessary spelling guess; if a
phone-to-grapheme guess is used, it must preserve the original phone ownership.

Concrete precedents in this checkout:

- `taskrunners/utr/strategy.rs::plan_utr_alignment` aligns flattened word streams
  and projects indices through `word_to_utt` to recover utterance spans.
- `python/batchalign/backends/fa/whisper_fa.py` flattens source words and model
  tokens into characters with owner payloads, DP-aligns them, then projects
  matches back to source words. This is the closest structural template.
- `backends/compare.rs::levenshtein_align` uses the same edit-alignment pattern,
  with its own token matcher and traceback. It is not an existing ARPAbet path.
- `alignment/mod.rs::align` already accepts string tokens and returns indices,
  making it usable for phone-symbol DP without treating IPA code points as phones.

One adaptation matters: existing DP encodes substitutions as insertion/deletion
pairs. Copying only matched phones would erase pronunciation differences. The
projection layer must assign unmatched recognized phones to units too, with a
deterministic policy for runs between anchors and explicit ambiguity diagnostics
at word boundaries. Never synthesize missing acoustic phones from the reference.
One-to-many normalization mappings must not duplicate or split original phones
across units. Entirely unmatched units need a reviewed CHAT representation or an
explicit unresolved outcome. Copy explicit pauses structurally.

ARPAbet is a reasonable English starting alphabet; multilingual support needs a
shared inventory that retains the relevant distinctions on both sides. Keep this
normalization pluggable and retain full IPA regardless of comparison normalization.

## Build constraint: ordinary Rust/Python dependencies

The user requires this feature to build through the normal Rust/Python dependency
workflow. Do not introduce system speech packages, external G2P executables,
manual toolchain installation, or dictionary/model downloads in build scripts.

No particular pronunciation dictionary or G2P package is required. Choose the
provider based on language coverage, unknown-word handling, and packaging;
CMUdict is only one candidate for English. The
[Python package](https://pypi.org/project/cmudict/) currently publishes a
`cmudict-1.1.3-py3-none-any.whl` containing the dictionary; its declared dependencies
are `importlib-metadata` and `importlib-resources`. This establishes a feasible
package-only lookup path, although installation in our Bazel/wheel environments
still needs verification. Alternatively, package a pinned upstream dictionary
snapshot with its license and parse it with ordinary Rust/Python code.

Use a checked-in IPA-to-comparison-symbol mapping and the existing Rust DP.
If dictionary lookup is used, preserve alternative pronunciations. For unknown words,
initially accept explicit pronunciation overrides or report an unresolved unit;
do not silently substitute spelling characters for phones. Any automatic G2P
fallback must separately satisfy the same dependency constraint.

Keep acoustic inference behind a lazy optional dependency extra using the
Torch/Transformers stack. Model downloads belong to explicit runtime model
loading, not compilation, test collection, or CLI help. Update pyproject and the
repository's uv/Bazel lockfiles through its standard workflows when implementing.
Acceptance includes a clean normal build and deterministic tests without model
weights or system G2P tools, plus a separate real-model CLI smoke test. This
investigation verifies packaging feasibility, not a completed clean build.

Implementation must happen in a separate git worktree: another agent is
refactoring the GUI in the current checkout. Only this investigation document
has been authored here for this task; no feature code has been changed.

## Proposed integration

Names below are proposed, not existing API:

| Layer | Addition |
|---|---|
| CLI | `phonetic` command with engine/model/device and existing input/output conventions |
| Recipe | `recipes.phonetic(phonetic_backend=..., ...)` |
| Task | `Task.Phonetic`, task name/provenance, task enumeration and ordering |
| Backend marker | Python `Phonetic` marker and task discovery registration |
| Protocol | `PhoneticInput` / `PhoneticOutput`, closed unions, schema registration and Python wire mappings |
| Runner | `PhoneticTaskRunner`, canonical registration, audio preparation, extraction, dispatch, validation and tier injection |
| Backend | Lazy-loaded `PhoneticXeusBackend`, optional dependencies and Bazel lock/build integration |

Implementation anchors are `python/batchalign/recipes.py`,
`python/batchalign/backends/base.py`, `python/batchalign/_core/proto.py`,
`python/batchalign/cli/__init__.py`, and the core crate's `base.rs`, `proto/`,
and `taskrunners/`. Follow `taskrunners/fa.rs` for media preparation and timing
access, and the existing tier-writing runners for AST mutation. Some FA helpers
are private and need deliberate extraction into shared utilities.

Use the engine's existing batching, caching, progress, and provenance. Inputs
should carry prepared audio and stable utterance/unit identifiers plus relevant
timing windows when used. Outputs should preserve phone tokens; acoustic spans
are optional. Cache identity must include audio, crop/timing inputs, reference
units, pronunciation/normalization versions, model/code revision, and decoding settings;
do not copy FA's deliberate exclusion of timing bounds into this new task.

The recipe must explicitly include optional timing stages: the engine's
`requires()` edges order declared tasks but do not insert missing tasks. For a
first release, accept existing CHAT plus audio with utterance windows. Compose
UTR when window recovery is needed, and ASR/segmentation when starting from raw
media. FA can supply optional evidence but is not a prerequisite for phone DP.

Preserve existing `%pho` by default. An explicit replacement mode must also
handle stale derived `%xphosyl` and `%xphoaln` annotations. Stage changes before
mutation, enforce output/input correspondence, and validate the resulting CHAT.

## First implementation and acceptance gates

1. Run the pinned model on a small, manually checked TalkBank sample; measure
   runtime, peak memory, phone errors and boundary-assignment errors separately.
2. Prototype comparison-alphabet DP and boundary projection on simple utterances.
   Include actual pronunciation substitutions, inserted/deleted phones, repeated
   phones across word boundaries, alternative pronunciations and unknown words.
   Expand to CHAT-specific cases with explicit mappings and fixtures.
3. Add the typed task, runner, backend, recipe and CLI. Test with a deterministic
   fake backend before exercising the downloaded model.
4. Cover IPA round trips, multi-code-point phones, pauses, retraces, replacements,
   groups, missing media/timings, empty predictions, existing tiers, idempotence,
   and cache invalidation. Ensure failure never yields a silently shifted tier.
5. Run repository checks through `just batchalign pytest` / `just batchalign test`
   and real integration through `just batchalign cli phonetic ...` once implemented.

Recommendation: proceed with an experimental command using phone-alphabet DP
and projection, reusing the existing BA alignment pattern. The model adapter and
DP machinery are straightforward; normalization, unmatched-phone ownership and
corpus-specific evaluation should gate broader availability.
