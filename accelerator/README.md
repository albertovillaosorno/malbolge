# Replaceable accelerator boundary

`accelerator/` owns optional execution capacity behind hardware-neutral exact
contracts. Accelerator results never become semantic authority merely because a
GPU produced them.

The first implemented port is `ExactPrimitiveAdapter`, which batches classic
Malbolge `rotate` and `crazy` over the exact 59,049-word domain.
`ClassicStepRequest`/`ClassicStepResult` represents one specification-mode classic
VM transition over at most four explicitly declared memory cells.
`ClassicRunRequest`/`ClassicRunResult` carries one complete 59,049-word classic
state through bounded resident execution. `ProfileRunGeometry` plus
`ProfileRunRequest`/`ProfileRunResult` extends that boundary to validated
single-word-modular ternary profiles without embedding CUDA identity. The current
14-trit/4,782,969-word profile now executes through the same geometry-bound CUDA
kernel model. `accelerator/cpu/` remains the mandatory scalar primitive reference;
CUDA results are checked against normative Rust execution. Compiler and verifier
code do not import CUDA APIs.

Missing accelerator hardware changes availability/performance only. Malformed
requests fail in the shared contract before backend execution; accelerator
runtime failures are explicit and never silently change acceptance rules.
`resource_budget.py` additionally owns hardware-neutral measured resource
snapshots and deterministic resident chunk planning; it does not know CUDA APIs.

Rust product batches now route through hardware-neutral optional backends with
safe-Rust fallback. RTX 4060 current-profile evidence now includes device-side
shared-state replication and persistent scalable sessions. Complete-snapshot
batch 32 reaches about 51.67 VMs/s, while resident batch 128 reaches about
2.00 million 64-step segments/s when setup and snapshots are outside the timed
region. `ProfileMemoryImage` now carries reusable geometry-bound validation proof;
retained batch-32 complete-snapshot throughput reaches about 93.68 VMs/s and
validation/planning falls to about 0.23 ms. Direct complete-snapshot materialization now downloads into final result
arrays without redundant packed host staging. `CudaProfileRunSession.profile_snapshot()`
adds a diagnostic-only decomposition of fresh host-array allocation,
state/memory/output D-to-H, decode, and inclusive total while ordinary `snapshot()`
remains unchanged. Retained RTX 4060 evidence records 3.1616/65.7829/271.1391 ms
for batches 1/8/32. Batch 1 is 96.489% memory transfer; batches 8/32 are about
62--64% fresh arrays and 36--37% memory transfer. Ordinary resident snapshots now always own fresh independent mutable
`array('I')` memories. The explicit
`caller-owned-independent-u32-arrays-v1` workspace allocates those arrays once and
advertises that later calls overwrite earlier aliased results. Retained RTX 4060
batches 1/8/32 improve by 2.586x/2.667x/2.712x with median-derived crossover
1/2/2 snapshots. Batch-one advantage is marginal; repeated batches 8/32 recover
allocation on the second snapshot. Explicit
`bounded-all-or-pageable-u32-arrays-v1` host registration now page-locks all
workspace arrays only within a caller-supplied byte budget. Retained RTX 4060
batches 1/8 improve 1.079x/1.108x with crossover 2/3; a 256 MiB budget forces
batch 32 to `budget-exceeded` pageable fallback. Ordinary snapshots and default
workspaces remain pageable. The explicit `caller-owned-windowed-u32-arrays-v1`
stream workspace now reuses a fixed host-memory window across ordered callbacks.
Retained batch-32 windows 1/8 reduce host memory 96.875%/75.000% and improve
1.023x/1.036x versus the full pageable window. Evidence is retained under
`benchmarks/accelerator/evidence/2026-07-29-current-profile-snapshot-stream-window-tradeoff-rtx4060/`.
Callback-scoped aliases must be copied before the next window when durable ownership
is required. CUDA runtime identity `cuda-ordered-registered-dtoh-stream-v1` now binds
ordered D-to-H submission with default-stream dependencies to same-context registered buffers. Pending
copies retain host registration until `wait()` or teardown, and runtime close drains
streams before unregistering host memory. The explicit
`caller-owned-double-window-overlap-u32-arrays-v1` workspace now retains two equal
registered banks and submits the next D-to-H window while the current callback
validates or consumes its aliases. One-bank budgets and registration disable,
budget, or Driver rejection preserve exact synchronous fallback. Retained evidence
under `benchmarks/accelerator/evidence/2026-07-29-current-profile-snapshot-double-buffer-overlap-rtx4060/` records matched window-1/8
speedups of 1.003x/1.012x with 14/15 and 15/15 paired wins, while retained memory
and setup roughly double. It is therefore opt-in; no kernel overlap or semantic
authority changes. `work_ports.py` now defines hardware-neutral candidate evaluation, search
execution, verification-assist, and trusted-admission boundaries. CPU callback
adapters provide mandatory candidate/search execution capacity while search
proposals and verification hints remain untrusted. `submission.py` adds
`validated-candidate-submission-v1`: an exact candidate batch is bound to one
optional ticket and a deferred CPU reference route. Results remain unpublished
until `wait()` validates capability, evaluator identity, count, and request order.
Pending tickets must close before fallback; malformed tickets and cleanup failure
fail closed. State and actual/fallback route are observable, repeated successful
wait is idempotent, and close-before-wait prevents execution. The contract creates
no hidden threads. CUDA now implements this port for exact classic crazy/rotate
candidates. Runtime identity `cuda-independent-stream-kernel-launch-v1` gives every
one-shot ticket one nonblocking Driver stream, exact parameter/buffer ownership,
stream-specific synchronization, and deterministic destruction. Launch rejection
cleans the new stream; synchronization failure still attempts destruction; runtime
close drains all outstanding ticket streams. Five deterministic tests cover both
stable launch identities, distinct handles, selected-stream wait, launch cleanup,
and synchronization-failure cleanup. Seven live RTX 4060 routes cover rotate,
crazy, empty/idempotent, close-before-wait, adapter-teardown fallback, and reverse
waiting of two tickets; that route passes 50/50 stress. Existing synchronous
primitive calls retain `cuda-default-stream-kernel-launch-v1`. Retained evidence
under `benchmarks/accelerator/evidence/2026-07-29-independent-ticket-stream-throughput-rtx4060/` records sequential/grouped medians for groups 2/4/8 of
2.1745/1.5970, 3.6403/3.0304, and 7.5313/5.6971 ms, improvements of
1.362x/1.201x/1.322x with 15/15 paired wins each. The opt-in
`cuda-independent-stream-kernel-timeline-v1` path adds a synchronized origin and
start/end events around each exact launch while ordinary tickets remain event-free.
Three deterministic timeline tests cover ordering, active lifetime, overlap, and
failure cleanup; one live test preserves exact output. Retained evidence under
`benchmarks/accelerator/evidence/2026-07-29-independent-ticket-event-timeline-rtx4060/` uses the same workload SHA: groups 2/4/8 overlap in 2/15, 8/15, and
15/15 samples, with median overlap 0/0.006144/0.015360 ms, concurrency
1.000x/1.072x/1.091x, and maximum peaks 2/3/5. This is positive origin-relative
event-interval attribution, not pure kernel duration, SM occupancy, or
kernel-transfer overlap.
Opt-in `cuda-independent-stream-ticket-transfer-v1` now registers exact
input/output host buffers and enqueues H-to-D, kernel, and D-to-H work on the
ticket's same nonblocking stream. Five deterministic runtime tests cover
ordering, leases, and partial-failure cleanup; four live candidate routes cover
no synchronous-copy use, crazy exactness, reverse waiting, and teardown
fallback. Retained evidence under
`benchmarks/accelerator/evidence/2026-07-29-independent-ticket-transfer-throughput-rtx4060/`
records 210 chronological samples over 14 routes. The group-eight hypothesis
fails: streamed grouped is 12.0138 ms versus 5.9408 ms synchronous grouped, a
0.494x ratio and 0/15 paired wins, despite improving 1.118x over streamed
sequential with 14/15 wins. Synchronous copies therefore remain the default and
streaming remains an exact explicit experiment. Wall time alone does not
attribute physical transfer/kernel overlap.
Opt-in `cuda-independent-stream-ticket-transfer-timeline-v1` now records four
contiguous CUDA events around upload, exact kernel, and download on each
streamed ticket. Three deterministic tests cover phase order, active lifetime,
and failed-kernel cleanup; one live RTX 4060 test preserves CPU-equal output and
monotonic phases. Retained evidence under
`benchmarks/accelerator/evidence/2026-07-29-independent-ticket-transfer-event-timeline-rtx4060/`
contains 45 grouped observations and 210 ticket phase rows. Groups 2/4/8 record
0.000000 ms median transfer/kernel overlap and 0/15 significant samples each, so
the group-eight hypothesis fails. Group-eight upload/kernel/download sums are
0.956352/0.340768/0.588512 ms versus 12.9495 ms wall time; only about 14.6% of
the instrumented wall interval is represented by those summed device phases.
This closes phase attribution for the retained workload, not a universal claim
that CUDA hardware can never overlap transfers and kernels.
Hardware-neutral `evidence-bound-ticket-route-admission-v1` now gives ticket
grouping an explicit evidence gate. It validates exact backend, device, and
workload identity plus exact output, lower candidate median, and a strict
paired-win majority; malformed or duplicate route records fail closed. Plans
preserve input order, minimize chunk count, then measured median cost, and
prefer synchronous ties. The retained
`rtx4060-full-domain-crazy-ticket-admission-2026-07-29-v1` profile binds the RTX
4060 `sm_89` capability and full-domain CRAZY workload to source commit
`431f542ab6321eeb12b7bcb9195318f25cf376a5`. It admits synchronous groups 2/4/8
and rejects streamed routes 1/2/4/8; a ten-ticket queue therefore selects groups
2+8 at a 7.3271 ms estimated median. The opt-in executor validates the packed
workload SHA-256, reverse-waits each group, restores input order, and closes
every ticket. Sixteen admission tests cover fallback, positive/negative
evidence, duplicate/malformed records, exact profile matching, and two live CUDA
routes. The seven route records and exact provenance now live in schema-v3
`accelerator/cuda/ticket_admission_profiles.json`, not Python source.
`benchmarks/accelerator/ticket_admission_profile_manifest.py` reconstructs those
canonical bytes from the retained JSON/TOML bundle, source commit, exact raw/
structured-output hashes, the tracked CUDA toolchain manifest, and retained driver
build. Nine manifest tests require byte equality and reject duplicate or unknown
keys, unsupported schema, duplicate routes, malformed display versions, and direct
capability/runtime mismatch. Runtime loading reads only the tracked product
manifest and never opens benchmark evidence. `cuda-runtime-toolchain-identity-v1`
is measured when the adapter opens: `cuDriverGetVersion` must be at least 13030,
`nvrtcVersion` must be exactly 13.3, the SHA-256 of
`accelerator/cuda/toolchain.json` must match, and optional NVML must report display
build `610.88` for this profile to resolve. Missing or failed NVML leaves ordinary
CUDA available but this evidence-bound profile unmatched. Twelve runtime-identity
tests cover fake query/hash success, Driver/NVRTC/read failures, missing NVML,
NVML init/query/shutdown failures, and one live CUDA route. Other display-driver
builds, cross-device evidence, and other workloads remain open. The global
synchronous default does not change.
`search_submission.py` adds
`validated-search-submission-v1`: one exact algorithm/problem/seed/budget request
binds an optional ticket and deferred CPU search. Proposal publication waits for
capability/algorithm/seed/budget validation; cleanup must succeed before fallback.
Malformed tickets fail closed, successful wait is idempotent, mandatory failure is
cached, and close-before-wait prevents execution. Ten tests cover the complete
neutral lifetime. Proposals remain untrusted and require `admit_search_result` for
independent acceptance. `classic-rotate-target-search-submission-v1` is the first
concrete composition: it retains full-batch selector state, submits only the exact
zero-or-one preimage projection through a candidate ticket, and publishes against
the full batch after candidate validation. Eight tests cover identity, projected
and empty CPU routes, malformed nested evidence/ticket behavior, and three live
RTX 4060 routes: exact one-position publication, empty projection, and adapter-
teardown CPU fallback. This is lifetime/exactness evidence, not measured speedup or
independent-stream overlap. Other strategies and ROCm search tickets remain open.
`verification_submission.py` adds
`validated-verification-assist-submission-v1`. Optional assistance remains pending
until `wait()`; no backend, typed submit/wait failure, or malformed result completes
with no hints only after any known ticket closes. Malformed tickets and cleanup
failure fail closed, successful waits are idempotent, and close-before-wait blocks
publication. Nine tests cover the neutral state/outcome lifetime.
`candidate-evidence-verification-submission-v1` composes exact candidate tickets
into ordered optional hints while retaining evaluator/verifier identity. Seven tests
cover CPU evidence, malformed nested evidence/ticket, verifier mismatch, and two
live RTX 4060 routes: exact CUDA hints and teardown-driven empty completion. Hints
remain untrusted; only `TrustedCandidateVerifier` may accept a proposal. No hint-
ticket speedup or independent-stream claim is made.
`search_selection.py` independently resolves algorithm and backend bindings,
requires a CPU reference, supports explicit overrides, and records configured
versus actual backend identity after fallback. `search_config.py` adds versioned
TOML base selection with fail-closed schema/identity validation and durable source
identity; explicit overrides produce a new effective selection without mutating
the loaded configuration. `primitive_candidates.py` binds
classic crazy/rotate candidate payloads to any exact primitive adapter; the same
bridge is differentially exercised through CPU and live CUDA backends.
`evidence_verification.py` reuses candidate evidence as optional verification
hints without introducing backend acceptance authority, and live CUDA hints match
the CPU reference over a deterministic 257-item corpus. `evaluated_search.py`
adds a bounded map/select search adapter that only proposes members of the exact
evaluated batch. `classic-rotate-target-search-v1` uses a zero-or-one inverse
projection. `classic-crazy-target-search-v1` proves the general multiposition case
without heuristic filtering: neutral `CRAZY_TRIT_TABLE` semantics derive exact
fixed-accumulator preimage positions, full-batch membership remains authoritative,
and only the projected subset reaches CPU/CUDA evaluation. The canonical complete
59,049-word domain retains exactly 1,024 positions for accumulator zero and target
29,524. Fourteen strategy tests include a live RTX 4060 prepared CUDA result equal
to CPU with resident cardinality 1,024; three CLI tests cover CPU, CUDA, and setup
fallback. Trusted CPU admission remains separate. This is correctness evidence,
not a speedup or independent-stream claim.
`python -m optimizer.cli` is the first external search runner: it reads Search
Configuration v1 plus canonical problem bytes, accepts explicit algorithm/backend
overrides, and emits deterministic JSON containing problem SHA-256,
configured-versus-actual backend identity, device metadata, seed/budget, and only
untrusted proposals. Supported CUDA setup failure preserves configured CUDA intent
while safely falling back to CPU; unsupported algorithm/backend pairs fail
explicitly. The retained full-domain comparison at
`benchmarks/accelerator/evidence/2026-07-27-rotate-target-search-rtx4060/`
contains 15 samples per backend under Benchmark Protocol v1. CPU median is
401.185 ms and CUDA median is 412.570 ms over all 59,049 classic words, yielding a
0.972x CUDA/CPU ratio and rejecting the speedup hypothesis for this complete
host-heavy route. Proposals remain identical and independently admitted. This
negative result motivates larger or resident search designs rather than hidden
benchmark filtering. The retained phase profile at
`benchmarks/accelerator/evidence/2026-07-27-rotate-target-search-phase-profile-rtx4060/`
shows 97.5% CPU and 99.5% CUDA named-phase coverage. CUDA host-side phases account
for about 57.0% of median total time, backend evaluation about 42.5%, and batch
construction plus proposal selection about 173.081 ms.
`PreparedEvaluatedSearch` now carries immutable validated request/batch state bound
to exact algorithm, batch-builder, and selector identity. It can be prepared once
through CPU and reused unchanged through matching CPU or CUDA adapters; forged or
mismatched strategy state fails closed. Prepared execution and diagnostics avoid
repeated batch construction/validation, while rotate-target selection decodes only
the validated header target instead of rebuilding the complete corpus. The
ordinary-versus-prepared evidence is retained under
`benchmarks/accelerator/evidence/2026-07-28-prepared-search-rtx4060/`. CPU median
falls from 293.564 to 148.590 ms (1.976x), and CUDA median falls from 306.872 to
162.693 ms (1.886x). Prepared CUDA remains about 9.5% slower than prepared CPU
(0.913x CPU-prepared/CUDA-prepared). These are amortized repeated-search results;
preparation is outside the timed interval. The retained prepared phase profile at
`benchmarks/accelerator/evidence/2026-07-28-prepared-search-phase-profile-rtx4060/`
shows backend evaluation consuming 79.9% of CPU and 81.2% of CUDA median total
time; proposal selection consumes 19.6% and 18.7%. Proof/result validation is
negligible. `PackedCandidateEvidence` now implements that boundary with one
fixed-width opaque payload buffer whose logical identities are inherited from the
validated batch order. Generic item results remain compatible; width, size, and
mixed-form drift fail closed. Primitive search iterates packed u32 values without
per-candidate bytes/objects, while verification-assist materializes only at the hint
boundary. Retained evidence under
`benchmarks/accelerator/evidence/2026-07-28-packed-search-rtx4060/` lowers CPU
ordinary/prepared medians to 211.693/77.309 ms and CUDA medians to
230.144/91.199 ms, improvements of 1.387x/1.922x and 1.333x/1.784x over the
pre-packed routes. The sibling packed phase profile lowers backend evaluation to
53.907 ms CPU and 67.202 ms CUDA. Packed CUDA prepared remains about 18.0% slower
than packed CPU prepared. `PreparedCandidateExecution` now lets a strategy attach
hardware-neutral decoded candidate state to the existing proof. Rotate search
prepares one validated `PrimitiveBatch`; matching CPU/CUDA adapters consume it
without repeated candidate batch validation or payload decode. The preparer is
part of strategy identity, and forged type/kind/evaluator state fails closed.
Ordinary one-shot search still prepares locally. Retained evidence under
`benchmarks/accelerator/evidence/2026-07-28-prepared-primitive-search-rtx4060/`
records 43.129 ms CPU and 57.296 ms CUDA prepared medians, 1.792x/1.592x faster
than the packed baseline. Ordinary routes regress 6.6%/3.7%, and prepared CUDA
remains 32.8% slower than prepared CPU. The phase bundle lowers backend evaluation
2.801x CPU and 2.083x CUDA. `PreparedPrimitiveBatch` now carries reusable exact
validation proof. CPU consumes it directly; CUDA prepared execution keeps one
proof-bound input/output allocation resident and rebuilds only when proof identity
changes. Ordinary CUDA stays one-shot. `CudaPreparedPrimitiveStats` and the prepared
benchmarks require one build, 16 evaluations, 15 reuses, and 59,049 resident rotate
words. Retained evidence under
`benchmarks/accelerator/evidence/2026-07-28-resident-primitive-search-rtx4060/`
records 34.132 ms CUDA prepared versus 46.232 ms CPU prepared: a 1.355x same-run
CUDA advantage and 1.679x CUDA improvement over the pre-resident baseline. The
phase sibling lowers CUDA backend evaluation 3.252x to 9.922 ms, but complete phase
total stays at 55.910 ms because selection rises to 46.331 ms. Proposal
selection/membership validation selected the next boundary.
`PreparedEvaluatedSearch` now stores a `frozenset` of exact `(logical_id, payload)`
pairs built after batch validation. Prepared CPU/CUDA validation reuses it; ordinary
search remains one-shot, and forged payloads fail closed. Both prepared benchmarks
require exactly 59,049 indexed members. Retained evidence under
`benchmarks/accelerator/evidence/2026-07-28-indexed-membership-search-rtx4060/`
records 26.797 ms CPU prepared and 17.970 ms CUDA prepared, 1.725x/1.899x faster
than the resident baseline. CUDA prepared is 1.491x faster than same-run CPU. The
phase sibling lowers proposal selection 3.519x CPU and 3.939x CUDA to
11.801/11.761 ms. Improved controls bound total attribution.
`PreparedProposalSelection` now binds strategy-specific selector state into the
prepared proof. Rotate target preparation computes the unique classic rotate
preimage after pruning/seed/budget and retains its evaluated positions. Prepared
selection validates only those packed evidence words; ordinary search keeps the
full scan. Missing/excluded positions, forged state, and nonmatching evidence fail
closed, and benchmarks require one prepared position. Retained evidence under
`benchmarks/accelerator/evidence/2026-07-28-direct-rotate-selection-rtx4060/`
records 15.266 ms CPU prepared and 6.182 ms CUDA prepared, improvements of
1.755x/2.907x over indexed membership. CUDA is 2.470x faster in the same run. The
phase sibling lowers selection to 13.2/12.4 us (894.008x/948.452x), while backend
phases change only 1.034x/1.035x. Primitive result validation now checks exact
minimum/maximum tuple bounds rather than a Python per-value loop, preserving
negative/overflow rejection before packing. Retained evidence under
`benchmarks/accelerator/evidence/2026-07-28-extrema-validation-search-rtx4060/`
records 14.058 ms CPU prepared and 4.929 ms CUDA prepared, improvements of
1.086x/1.254x over direct selection. Backend phases improve 1.091x/1.330x while
ordinary controls remain nearly flat. Prepared CPU rotate now reuses a cached
59,049-entry table generated from the scalar reference formula. Ordinary CPU stays
scalar, the exhaustive test compares every classic word, and benchmarks require
16 prepared evaluations plus the full table cardinality. Retained evidence under
`benchmarks/accelerator/evidence/2026-07-28-cpu-rotate-table-search-rtx4060/`
records 3.313 ms CPU prepared, 4.243x faster than extrema validation and 1.440x
faster than same-run CUDA. The phase sibling lowers CPU backend evaluation 4.540x
to 2.906 ms while CUDA changes only 1.018x. `PackedPrimitiveResult` now carries
canonical little-endian u32 words alongside tuple results. Prepared CUDA returns the
resident host buffer as bytes after D-to-H transfer; the candidate bridge validates
capability, exact byte count, and every classic-domain word before forwarding those
same bytes. Ordinary CUDA and CPU tuple routes remain unchanged. Benchmarks require
`packed_evaluations=16` with the existing proofs. Retained evidence under
`benchmarks/accelerator/evidence/2026-07-28-packed-cuda-primitive-search-rtx4060/`
records 2.036 ms CUDA prepared, 2.343x faster than the CPU-table baseline and
1.621x faster than same-run CPU. The phase sibling lowers CUDA backend evaluation
2.147x to 1.802 ms while CPU changes only about 0.5%. Packed-domain validation
now uses `u32le-broadword-domain-v1`: repeated high-bit masks plus an independent
per-lane threshold addition validate all u32le words in big-integer operations.
Invalid first/last threshold or high-bit lanes retain descriptive fail-closed
fallback. Benchmarks require the validator identity. Retained evidence under
`benchmarks/accelerator/evidence/2026-07-28-broadword-packed-validation-search-rtx4060/`
records 1.175 ms CUDA prepared, 1.733x faster than scalar packed validation and
2.706x faster than same-run CPU. The phase sibling lowers CUDA backend evaluation
2.095x to 0.860 ms and CUDA total 2.057x to 0.886 ms; CPU phase regressions remain
controls. `CudaPreparedPrimitivePhaseProfile` now records resident launch/sync,
D-to-H, immutable bytes, and total time. `PackedPrimitiveEncodingPhaseProfile`
records the historical broadword contract, masks, integer decode, checks,
diagnostics, result build, and total. Prepared candidate state now additionally
retains immutable CPU truth under `cpu-reference-packed-equality-v1`; ordinary
results continue to use `u32le-broadword-domain-v1`. Prepared CPU/CUDA output must
match all retained bytes after capability, representation, and exact-count checks,
so incorrect in-domain first or final words fail closed. The generic search adapter
exposes proof-bound candidate-state cardinality, and full-domain benchmarks require
59,049 reference words plus all existing table/session/membership/selector proofs.
The prepared profiler now records contract, exact compare, result build, visible
layer residuals, CUDA phases, and end-to-end total. Retained evidence under
`benchmarks/accelerator/evidence/2026-07-28-prepared-reference-search-rtx4060/`
records 0.488 ms CUDA prepared, 2.407x better than broadword and 6.786x faster than
same-run CPU. The search-phase sibling records 0.215 ms CUDA backend evaluation
(3.999x) and 0.238 ms total (3.729x). The primitive profile records 0.0278 ms exact
validation (23.590x better), 0.0180 ms byte comparison, and 0.1935 ms end-to-end
(4.488x). Reference construction is untimed and the full-domain image consumes
236,196 bytes. `search_preparation_crossover.py` now measures cold/warm preparation,
incremental Python allocation, fresh resident build, steady reuse, and strict
ordinary/prepared crossover at 1/64/1,024/59,049 candidates. It preserves both
validator IDs, exact proposals/admission, state cardinalities, and CUDA session
proofs. Retained evidence under
`benchmarks/accelerator/evidence/2026-07-28-prepared-search-crossover-rtx4060/`
records warm crossover 6/3/2/1 and cold crossover 106/38/5/2. Full-domain warm
preparation plus first search is 212.140 ms versus 222.842 ms ordinary; cold crosses
on run two. Incremental Python state retains/peaks at 16.063/19.040 MiB versus
0.901 MiB exact reference/device/host buffers. Component tracing selected the historical membership frozenset as the first safe
compaction target. Prepared search now uses
`identity-sorted-candidate-reference-binary-search-v1`: an immutable, proof-bound,
identity-sorted tuple of references to the original batch items. Membership uses
binary search by logical ID followed by byte-exact payload equality; forged indexes,
cross-batch reuse, missing IDs, and payload substitution fail closed. Retained
version-2 evidence under
`benchmarks/accelerator/evidence/2026-07-28-compact-membership-crossover-rtx4060/`
records 473,352 bytes retained for the compact component versus 5,876,552 bytes for
the copied set at full domain (91.945% lower), with 15.851/18.027 ms preparation
(1.137x compact advantage). Complete prepared state falls from 16.063 to 10.910 MiB
retained and from 19.040 to 14.080 MiB peak. Exact hit/miss lookup regresses
9.898x/13.856x, so the index is promoted for scale memory/preparation rather than
lookup speed. Warm/cold crossover is 7/3/2/1 and 108/38/5/1. The trusted verifier
remains the sole proposal-admission authority. This is the retained version-2
baseline.
Retained version-3 evidence under
`benchmarks/accelerator/evidence/2026-07-28-indexed-candidate-batch-crossover-rtx4060/`
promotes proof-carrying fixed-width candidate storage for large deterministic
batches. At 59,049 candidates, complete prepared state falls from 10.910 to 2.923
MiB retained (73.211%) and from 14.080 to 8.395 MiB peak (40.378%). Warm/cold
preparation improves from 194.917/207.761 ms to 117.753/132.553 ms
(1.655x/1.567x), while ordinary CUDA search improves from 222.518 to 152.998 ms
(1.454x). Warm/cold preparation plus first resident search is 129.508/144.308 ms,
so both retain one-run crossover with 23.490/8.691 ms observed margins. The
rotation-backed membership component retains 528 bytes versus 473,352 bytes in
version 2 and 11,180,412 bytes for the same-run copied set; its preparation is
0.0177 ms versus 15.8507/155.4303 ms. Exact hit lookup is the retained cost:
17.755 microseconds versus 2.625 microseconds in version 2 and 0.266 microseconds
copied (6.763x/66.844x slower). Exact miss lookup improves to 0.636 microseconds
from 2.785 microseconds in version 2, but remains 3.094x slower than copied-set
miss lookup. The promotion is not universal: one-candidate memory grows slightly,
and 64-candidate cold/warm crossover moves from 38/3 to 45/4. Duplicate or
out-of-domain indexes, malformed widths/sizes, incorrect pivots, forged or
cross-batch proofs, and payload substitution still fail closed. Retained version-4 evidence under
`benchmarks/accelerator/evidence/2026-07-28-packed-prepared-primitive-crossover-rtx4060/`
promotes `proof-bound-u32le-primitive-input-v1`. At 59,049 candidates,
incremental retained prepared state falls from 3,064,623 to 713,791 bytes, a
76.709% reduction and 12.088 bytes per candidate. Peak allocation remains exactly
8,802,328 bytes (8.395 MiB): preparation still builds a temporary CPU
reference/decode tuple, so the result removes retained ownership rather than the
transient peak. Full-domain cold/warm crossover remains 1/1. Against the immediate
clean `81d82cf` baseline, CPU ordinary/prepared improve from 139.517/3.316 ms to
132.848/3.261 ms (1.050x/1.017x), while CUDA ordinary/prepared improve from
152.055/0.449 ms to 144.440/0.429 ms (1.053x/1.047x). Phase totals are 2.9664 ms
CPU (1.006x) and 0.2654 ms CUDA (1.099x). CPU and CUDA both prove one session
build, 16 evaluations, 15 reuses, rotate kind, and 59,049 resident words; CUDA
also proves 16 packed evaluations and CPU proves the full rotate table. The packed
representation is promoted because no clean route regresses. Retained version-5 evidence under
`benchmarks/accelerator/evidence/2026-07-28-packed-rotate-batch-builder-crossover-rtx4060/`
promotes `classic-u32le-bitset-first-representatives-v1` with independent
`cpu-scalar-packed-equality-v2`. At 59,049 candidates, cold/warm preparation falls
from 122.990/109.027 ms to 76.130/76.584 ms (1.616x/1.424x), retained state falls
slightly from 713,791 to 710,647 bytes, and peak Python allocation falls from
8,802,328 to 1,183,023 bytes (86.560%). Full-domain crossover remains 1/1. CPU
ordinary/prepared improve from 132.848/3.261 ms to 90.869/3.108 ms
(1.462x/1.049x), while CUDA ordinary improves from 144.440 to 103.562 ms
(1.395x). CUDA prepared throughput is the retained contextual negative at
0.479 versus 0.429 ms (0.896x); the separate prepared CUDA phase total changes
only from 0.2654 to 0.2676 ms (0.992x), so no prepared-execution effect is
attributed to the builder. The fixed bitset raises one-candidate peak from 2,664
to 8,391 bytes and 64-candidate warm crossover from 3 to 4 runs; promotion is for
large deterministic batches, not universal small-batch memory. All builder,
storage, validator, membership, proposal, admission, cardinality, and CPU/CUDA
session proofs pass. Component attribution now places the remaining peak in the
batch builder: it reaches about 1,183,087 bytes while retaining 473,546 bytes as
representative, selected-index, and payload arrays coexist. Retained version-6 evidence under
`benchmarks/accelerator/evidence/2026-07-28-inplace-packed-batch-builder-crossover-rtx4060/`
promotes `classic-u32le-bitset-inplace-first-representatives-v2`. At 59,049
candidates, cold/warm preparation falls from 76.130/76.584 to 64.606/65.101 ms
(1.178x/1.176x), peak Python allocation falls from 1,183,023 to 962,052 bytes
(18.679%), retained state remains 710,647 bytes, and full-domain crossover remains
1/1. CPU/CUDA ordinary routes improve from 90.869/103.562 to 79.943/92.133 ms
(1.137x/1.124x). Prepared controls move in opposite directions: CPU throughput is
3.267 versus 3.108 ms (0.952x), CUDA throughput is 0.385 versus 0.479 ms
(1.245x), and separate CPU/CUDA phase totals are 2.9659/0.2723 ms versus
2.9535/0.2676 ms (0.996x/0.983x). No prepared-execution effect is attributed to
the builder. One-candidate peak stays 8,391 bytes; at 64 candidates peak falls
8,788 to 8,635 bytes while sub-millisecond ordinary timing varies upward; at 1,024
candidates peak falls 22,155 to 19,116 bytes and ordinary CUDA improves. All
builder, storage, validator, membership, proposal, admission, cardinality, and
CPU/CUDA session proofs pass. Component attribution now places the builder phase
near 710,190 bytes peak while retaining 473,546 bytes. The overall ~962 KiB peak
occurs when that retained batch coexists with candidate-state creation (~237 KiB
incremental) or selector creation (~253 KiB incremental). Reducing this post-builder
coexistence without weakening exact reference, selection, membership, or admission
proofs is the next measured boundary.
Retained version-7 evidence under
`benchmarks/accelerator/evidence/2026-07-28-native-view-selector-crossover-rtx4060/`
promotes `classic-u32le-native-view-preimage-v2`. The same-run component
comparison preserves the one exact preimage at all four scales. At 59,049
candidates, selector peak falls from 252,597 to 1,885 bytes (99.254%), while
selector preparation changes from 3.7642 to 3.9644 ms, a retained 5.318%
regression. Complete preparation peak falls from 962,052 to 946,675 bytes
(1.598%); retained state remains 710,647 bytes. Cold/warm preparation changes
from 64.606/65.101 to 64.465/64.780 ms and full-domain crossover remains 1/1.
At one candidate, the native selector retains 56 bytes more and peaks 240 bytes
higher; total one- and 64-candidate peaks are unchanged. CUDA ordinary, fresh
build, and reuse timings remain contextual controls because selector preparation
is outside execution intervals. Candidate-state creation, approximately 237 KiB
incremental beside the retained batch, is the next measured preparation-memory
boundary; exact reference, selection, membership, proposal, and admission proofs
remain mandatory.
Retained version-8 evidence under
`benchmarks/accelerator/evidence/2026-07-28-projected-prepared-rotate-crossover-rtx4060/`
promotes selection-aware exact projection under
`classic-rotate-preimage-projection-v1`. Generic evaluated search prepares the
selector proof first, requires the projected sub-batch to preserve evaluator
identity and exact full-batch membership, binds projection callbacks into strategy
identity, and validates backend evidence against only that sub-batch. Proposal
membership and trusted admission still use all 59,049 evaluated candidates. The
classic rotate inverse has zero or one exact preimage, so the canonical full-domain
prepared state retains one reference word, one selected position, and one resident
CPU/CUDA word while full membership remains 59,049. Empty projections skip backend
execution; wrong evaluator, fabricated member, oversized projection, forged proof,
wrong evidence, and fabricated proposal still fail closed. Against the immediate
clean version-7 baseline, cold/warm preparation improves from 64.4648/64.7804 ms to
46.2706/46.6161 ms (1.393x/1.390x), retained state falls from 710,647 to 475,010
bytes (33.158%), peak allocation falls from 946,675 to 710,126 bytes (24.987%),
and crossover remains 1/1. CPU prepared throughput improves from 3.2402 to 0.0787
ms (41.172x), while CUDA prepared improves from 0.5116 to 0.2743 ms (1.865x).
Prepared backend-phase speedups are 218.4x CPU and 2.366x CUDA; total prepared-phase
speedups are 52.8x and 1.914x. Ordinary CPU/CUDA changes are contextual controls and
are not attributed to projection. Projection is not universal tiny-batch policy: at
one candidate retained state rises from 1,863 to 2,349 bytes and cold/warm crossover
moves from 6/6 to 8/7. The required architectural boundary was an exact projected-subset contract for
strategies without a unique algebraic inverse. The promoted proof retains subset
identity, full membership, exact evidence, proposal validation, and independent
trusted admission rather than introducing heuristic filtering.
Retained version-9 evidence under
`benchmarks/accelerator/evidence/2026-07-28-exact-candidate-subset-crossover-rtx4060/`
promotes neutral `request-order-position-subset-v1` and rotate projection
`classic-rotate-preimage-position-subset-v2`. The proof binds immutable, strictly
increasing request-order positions to the exact full-batch object; empty, one-item,
and multi-item subsets are supported. Mutable, duplicate, reordered, out-of-range,
forged, wrong-type, and cross-batch state fail closed. Generic preparation validates
and unwraps the projection once, stores primitive state directly on the repeated hot
path, and retains the exact projected batch beside full membership authority. Formal
`candidate-subset-proof-tradeoff-v1` medians over 59,049 full-batch items compare
legacy membership revalidation with the proof route: 2.3/4.3 microseconds for empty
(0.535x), 20.0/7.5 microseconds for one item (2.667x), 1.0356/0.1581 ms for
64 items (6.550x), and 16.8647/2.5298 ms for 1,024 items (6.666x). The empty
proof adds 144 retained and 64 peak bytes; from one item upward retained memory is
slightly lower and peak memory is equal. Against the immediate clean version-8
baseline, full-domain cold/warm preparation improves from 46.2706/46.6161 ms to
45.7698/46.2938 ms, retained state falls by 32 bytes to 474,978 bytes, peak stays
710,126 bytes, and crossover remains 1/1. One-candidate crossover improves from
8/7 to 7/6, while 1,024 improves from 2/1 to 1/1. CPU prepared isolated throughput
regresses 2.8% (0.0787 to 0.0809 ms) and remains an explicit tradeoff; CPU prepared
phase total is exactly unchanged at 56.4 microseconds. CUDA prepared throughput
improves 0.5% and phase total improves from 141.4 to 141.1 microseconds. The proof
is promoted for exact authority and multi-item scaling, not as an empty-subset
optimization. That production boundary is now implemented by
`classic-crazy-target-search-v1`: exact digitwise preparation projects the full
59,049-member accumulator-zero/target-29,524 case to 1,024 positions before
replaceable CPU/CUDA evaluation. The full membership and independent admission
proofs remain unchanged. `classic-crazy-target-search-submission-v1` now carries
that full selector/projection proof across a deferred 1,024-item candidate ticket.
Seven tests cover full-domain/empty CPU routes, malformed nested protocol, live CUDA
publication, and teardown fallback. Retained evidence under `benchmarks/accelerator/evidence/2026-07-29-crazy-target-performance-matrix-rtx4060/`
records CPU ordinary/prepared medians of 368.3588/22.4264 ms (16.425x), CUDA
ordinary/prepared medians of 235.8490/20.3304 ms (11.601x), and a 185.7629 ms
one-shot CUDA ticket (1.270x over ordinary); every same-baseline comparison wins
15/15 retained pairs. CUDA prepared is 1.103x faster than CPU prepared and 9.137x
faster than the one-shot ticket. Prepared setup is untimed while ticket setup and
cleanup are timed. No cross-device, compiler, synthesis, kernel-overlap, or
independent-stream claim is made.
Synthesis/guided search, ROCm work ports and VM execution, broader hardware
evidence, richer orchestration, and additional representative comparisons remain
follow-on work. `optimizer/enumerative.py` supplies the first concrete CPU-only
search strategy: deterministic finite-corpus enumeration with canonical replay
identity and independent trusted verification.
