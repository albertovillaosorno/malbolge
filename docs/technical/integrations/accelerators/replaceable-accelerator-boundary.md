# Replaceable accelerator boundary

## Status

Active

## Purpose

Define a hardware-neutral interface for candidate evaluation, batch VM
execution, search, and verification. Compiler and verifier code must not depend
directly on CUDA APIs.

## Scope

This document governs the following declared TODO scope:

- `accelerator/`
- `algorithms/`
- `optimizer/`
- `benchmarks/accelerator/`
- `tests/optimizer/`

## Current Behavior

### Active Model

The shared accelerator surface is capability-oriented and hardware-neutral.
`accelerator/exact_primitives.py` defines immutable request/result/capability
types plus the `ExactPrimitiveAdapter` protocol. The first admitted operation
family batches classic ten-trit `rotate` and `crazy`; malformed shape or word
domain is rejected before any backend executes. `accelerator/classic_step.py`
adds a hardware-neutral fixed-width contract for one classic specification-mode
transition over an explicitly bounded memory snapshot. `accelerator/classic_run.py`
adds a complete-state bounded-run contract whose classic memory width is fixed at
59,049 words without exposing CUDA handles or layout details.
`accelerator/profile_run.py` extends the same hardware-neutral boundary to
validated single-word-modular ternary geometries, including the current
14-trit/4,782,969-word profile. `accelerator/work_ports.py` adds immutable
candidate-evaluation, search, and verification-assist request/result protocols.
Search requests bind algorithm ID, seed, and evaluation budget independently from
backend capability. Search proposals and verification hints carry no acceptance
bit; `TrustedCandidateVerifier` is the only admission port.

### Implementation Status

The first replaceable slice is implemented. `accelerator/cpu/` supplies the
mandatory scalar reference and `accelerator/cuda/` supplies an optional NVIDIA
adapter behind the same request/result contract. CUDA APIs occur only inside the
CUDA adapter. Compiler, verifier, VM, and shared accelerator code remain
hardware-neutral.

Backend capability records expose stable backend ID plus device name/architecture
for evidence. Accelerator unavailability and execution failure have distinct
typed errors; neither changes candidate validity or CPU-reference semantics. The
CUDA compact-step implementation is checked directly against Rust
`Machine::step_traced()` rather than promoted to semantic authority. Resident
classic and current-profile bounded execution are likewise checked against
complete normative Rust states. Rust product batch routing uses replaceable
backend traits with safe-Rust fallback and live CUDA-worker integration. Reported
routes expose per-item actual execution origin, distinguishing accepted backend
checkpoints from safe-Rust fallback and pre-backend admission rejection. The
legacy result-only routes remain wrappers that discard only that provenance. Live
CUDA product tests now require at least one accepted backend completion, so merely
configuring or invoking CUDA is not enough to claim the product route executed on
the device. Retained current-profile performance evidence additionally covers the
original complete
snapshot baseline, device-side shared initialization, and persistent resident
sessions. Resident full-snapshot diagnostics separate host allocation,
state/memory/output transfer, decode, and total. Ordinary snapshots now preserve
fresh independent mutable-memory ownership uniformly; the optional caller-owned
workspace is a distinct overwrite/alias contract bound to one live session. Neither
surface changes semantic authority or establishes a CPU-relative speedup.
Candidate evaluation/search/verification-assist ports are now active. The
portable CPU callback adapters provide mandatory candidate/search execution
capacity and best-effort routing falls back on typed optional-backend failures or
malformed result shape. Search selection now resolves algorithm/backend bindings
independently and records configured versus actual backend identity after
fallback. `accelerator/primitive_candidates.py` now maps exact classic crazy and
rotate candidate payloads into the existing primitive contract; the identical
bridge runs through mandatory CPU and optional CUDA adapters, and malformed
backend capability/count/domain evidence falls back before admission.
`EvidenceVerificationAssistAdapter` can expose that evidence as ordered optional
hints while preserving verifier-only acceptance. A live CUDA 257-item rotate
corpus matches CPU hints exactly; malformed optional evidence produces no hints.
`EvaluatedSearchExecutionAdapter` composes the candidate-evaluation port into a
bounded search route while preventing selectors from inventing payloads outside
the evaluated batch. `classic-rotate-target-search-v1` runs unchanged through CPU
or live CUDA evaluation; CUDA matches CPU proposals over 257 candidates and the
independent CPU verifier remains the only admission authority. A retained
full-domain performance comparison over 59,049 candidates keeps 15 samples per
backend and exact proposal checks. CPU median is 401.185 ms and CUDA median is
412.570 ms on the RTX 4060, yielding 0.972x CUDA/CPU and rejecting the speedup
hypothesis for this route. The diagnostic phase profile explains 97.5% of CPU
and 99.5% of CUDA median total time through named phases. CUDA host-side phases
account for about 57.0%, and batch construction plus proposal selection consume
about 173.081 ms. The neutral boundary now includes
`PreparedEvaluatedSearch`: immutable validated request/batch state bound to exact
algorithm, batch-builder, and selector identity. A CPU adapter may prepare it once
and a matching CUDA adapter may consume it without semantic reinterpretation;
forged or mismatched proof identity fails closed. Prepared execution preserves
result/proposal validation and verifier-only acceptance. Retained evidence records
1.976x CPU and 1.886x CUDA same-backend prepared improvements, while prepared CUDA
remains about 9.5% slower than prepared CPU. Preparation is outside timed intervals,
so the result applies to repeated immutable search state. The prepared phase
profile attributes 79.9% of CPU and 81.2% of CUDA median total time to backend
evaluation, with proposal selection at 19.6% and 18.7%. Candidate-evaluation result
representation/transport is now represented by `PackedCandidateEvidence`.
Fixed-width opaque payloads share one byte buffer and inherit IDs only from validated
request order; item-based adapters stay compatible, malformed width/size/mixed forms
fail closed, and materialization is explicit for consumers that need objects.
Retained packed evidence lowers every ordinary/prepared route median. The packed
phase profile reduces backend evaluation 2.326x on CPU and 2.058x on CUDA while
selection improves 1.369x/1.432x. Packed CUDA prepared remains about 18.0% slower
than packed CPU. The neutral proof now optionally stores prepared candidate state
under exact preparer identity. Rotate search validates and decodes one
hardware-neutral `PrimitiveBatch` during preparation, and matching CPU/CUDA
capacity consumes it without repeated request-order validation or payload decode.
Forged type/kind/evaluator state fails closed; strategies without a preparer retain
the ordinary adapter path. Retained prepared medians improve 1.792x CPU and 1.592x
CUDA, while ordinary routes regress 6.6%/3.7%. Prepared CUDA remains 32.8% slower
than prepared CPU. `PreparedPrimitiveBatch` now seals validated immutable input at
the exact primitive port. CPU consumes it directly; CUDA retains one proof-bound
input/output session and rebuilds only for different proof identity. Ordinary
execution remains one-shot. Explicit session statistics make residence observable.
Retained CUDA prepared throughput is 34.132 ms versus 46.232 ms CPU prepared,
showing a 1.355x same-run CUDA advantage. CUDA backend evaluation improves 3.252x,
while complete phase total does not improve because selection rises to 46.331 ms.
Prepared state now includes an immutable exact membership index constructed after
candidate batch validation. Matching CPU/CUDA routes reuse 59,049 identity/payload
pairs; ordinary execution keeps the one-shot dictionary path and forged payloads
remain rejected. Benchmarks expose/require the indexed count. Retained prepared
medians improve 1.725x CPU and 1.899x CUDA; selection improves 3.519x/3.939x to
11.801/11.761 ms. CUDA is 1.491x faster than same-run CPU. Improved controls bound
cross-run attribution. Prepared strategy state now optionally includes a
proof-bound selector preparer, selector, and count function. Rotate target uses the
exact classic inverse and stores only evaluated preimage positions; prepared
CPU/CUDA read and validate evidence there, while ordinary execution retains the
full scan. Forged/mismatched selector state and nonmatching evidence fail closed. Retained
prepared medians improve 1.755x CPU and 2.907x CUDA; selection improves
894.008x/948.452x to 13.2/12.4 us. CUDA is 2.470x faster than same-run CPU. Ordinary
controls and backend phases change far less, bounding attribution. Primitive
execution selected the next boundary. The neutral bridge now validates primitive
result tuples through exact minimum/maximum bounds, preserving negative and
above-domain failure before packing. Retained prepared medians improve 1.086x CPU
and 1.254x CUDA; backend phases improve 1.091x/1.330x and ordinary controls remain
nearly flat. Prepared CPU rotate now consumes a cached full-domain table generated
from the scalar reference; ordinary CPU remains scalar. Exhaustive equality and
benchmark counters make table use observable and fail closed. Retained CPU prepared
median improves 4.243x to 3.313 ms and CPU backend evaluation improves 4.540x to
2.906 ms. CPU ordinary is effectively unchanged, and CPU prepared is 1.440x faster
than same-run CUDA. The hardware-neutral result union now supports canonical
packed u32le words in addition to tuples. Prepared CUDA returns the copied resident
host buffer directly, while the neutral bridge remains authoritative for capability,
count, and complete domain validation. Ordinary CUDA, CPU, and test adapters retain
tuple compatibility. Benchmarks require 16 packed evaluations. Retained CUDA
prepared median improves 2.343x to 2.036 ms and CUDA backend evaluation improves
2.147x to 1.802 ms. CPU prepared/backend and ordinary controls remain effectively
flat, while CUDA prepared is 1.621x faster than same-run CPU. CPU result
validation now uses stable `u32le-broadword-domain-v1` identity. Repeated masks
reject high bits and detect values above 59,048 through lane-independent threshold
addition; scalar fallback exists only to describe invalid output. First/last-lane
threshold and high-bit corruption fail closed, and benchmark output requires the
identity. Retained CUDA prepared median improves 1.733x to 1.175 ms, CUDA backend
evaluation improves 2.095x to 0.860 ms, and CUDA total improves 2.057x to 0.886 ms.
CUDA is 2.706x faster than same-run CPU; CPU phase regressions remain contextual
controls. Public diagnostic phase records now cross the replaceable boundary
without carrying semantic authority: resident CUDA reports launch/sync, transfer,
immutable bytes, and total; neutral packed encoding reports contract, masks, integer
decode, high-mask, threshold, diagnostics, result construction, and total. The
prepared boundary now retains immutable CPU-reference bytes as strategy state and
validates prepared output with `cpu-reference-packed-equality-v1`; ordinary output
continues through `u32le-broadword-domain-v1`. The backend remains untrusted:
capability, immutable representation, exact count, full byte equality, proposal
membership, and independent verifier admission remain outside hardware authority.
First/final in-domain corruption fails closed. Generic state cardinality proves all
59,049 reference words, and benchmarks require both IDs plus existing execution
proofs. Retained evidence records 0.488 ms CUDA prepared search (2.407x), 0.215 ms
backend evaluation (3.999x), 0.238 ms search total (3.729x), 0.0278 ms exact
validation (23.590x), and 0.1935 ms primitive end-to-end (4.488x). Same-run CUDA is
6.786x faster than CPU prepared. The reference image is 236,196 bytes and construction
is excluded. A four-scale benchmark now measures fresh-process and warm-process
preparation, incremental Python memory, first resident execution, reuse, and strict
crossover while retaining every identity/admission/session proof. Retained
warm/cold crossover is 6/3/2/1 and 106/38/5/2. Full-domain warm one-shot saves
10.703 ms; cold crosses on run two. Incremental Python state retains/peaks at
16.063/19.040 MiB versus 0.901 MiB exact buffers. Component tracing selected the duplicate prepared membership frozenset for safe
compaction. The replacement is a proof-bound identity-sorted tuple of references to
the original immutable batch items. Binary search plus exact payload equality keeps
anti-fabrication checks outside accelerator authority, while forged/cross-batch
indexes fail closed. Retained version-2 evidence under
`benchmarks/accelerator/evidence/2026-07-28-compact-membership-crossover-rtx4060/`
records 91.945% lower full-domain component retention, 1.137x faster component
preparation, and 32.083%/26.051% lower complete prepared retention/peak. Exact
compact hit/miss lookup is 9.898x/13.856x slower than the copied set, so the
representation is promoted for scale memory/preparation rather than lookup speed.
Warm/cold crossover is 7/3/2/1 and 108/38/5/1. This is the retained version-2
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
optimization. The first production non-invertible/multi-position strategy is now
`classic-crazy-target-search-v1`. The normative ternary relation is owned by the
hardware-neutral `CRAZY_TRIT_TABLE`; one fixed accumulator and target derive every
exact request-order preimage position before backend execution. Full-batch
membership, evidence validation, proposal membership, and independent admission
remain unchanged. The complete 59,049-word corpus with accumulator zero and target
29,524 projects exactly 1,024 positions, and the same CPU-prepared state executes
unchanged on live RTX 4060 CUDA with resident cardinality 1,024. Fourteen strategy
and three CLI tests cover the boundary.
`classic-crazy-target-search-submission-v1` now retains the exact full-batch
selector/projection proof across a nested candidate ticket and submits only the
1,024-position subset. Seven tests cover identity, full-domain/empty CPU paths,
malformed nested evidence/ticket behavior, exact live CUDA publication, and
teardown-driven CPU fallback. Retained Benchmark Protocol v1 evidence under `benchmarks/accelerator/evidence/2026-07-29-crazy-target-performance-matrix-rtx4060/`
records CPU ordinary/prepared medians of 368.3588/22.4264 ms (16.425x, 15/15
paired wins), CUDA ordinary/prepared medians of 235.8490/20.3304 ms (11.601x,
15/15 wins), and a 185.7629 ms one-shot CUDA ticket (1.270x over ordinary,
15/15 wins). CUDA prepared is 1.103x faster than CPU prepared and 9.137x faster
than the ticket. Prepared setup is untimed; complete ticket preparation and cleanup
are timed. This is one-device deterministic workload evidence, not compiler,
synthesis, cross-device, kernel-overlap, or independent-stream evidence.
Resident/fused search remains later work. CUDA now
has the adapter-internal
`cuda-ordered-registered-dtoh-stream-v1` lifetime foundation: ordered submissions
retain same-context registered host buffers until synchronization and teardown.
The CUDA profile adapter now additionally owns explicit snapshot double buffering:
two fully registered host banks overlap next-window D-to-H with current callback
work and fail back synchronously when budget or registration admission is absent.
The shared boundary now additionally exposes
`validated-candidate-submission-v1` through `accelerator/submission.py`. It binds
one exact candidate batch to an optional backend ticket and deferred mandatory CPU
reference, publishes only after result validation, records pending/completed/closed/
failed state, and requires successful optional-ticket cleanup before fallback.
Malformed tickets or cleanup failure fail closed. The neutral layer creates no
threads and grants no acceptance authority. CUDA now implements candidate tickets
for exact classic crazy/rotate work through
`cuda-independent-stream-kernel-launch-v1`. Every ticket owns one nonblocking stream,
exact launch parameters, and private buffers until stream-specific wait, exact CPU
reference validation, and destruction. Launch/synchronization failure cleanup and
runtime draining are fail-closed. Five deterministic stream tests plus seven live
candidate tests cover identity, isolation, selected wait, exact output, and teardown;
reverse waiting passes 50/50 stress. Existing synchronous calls remain under
`cuda-default-stream-kernel-launch-v1`. Retained evidence under `benchmarks/accelerator/evidence/2026-07-29-independent-ticket-stream-throughput-rtx4060/` records
grouped-ticket improvements of 1.362x/1.201x/1.322x for groups 2/4/8, all 15/15
paired wins. Opt-in `cuda-independent-stream-kernel-timeline-v1` now attributes
origin-relative start/end intervals around the same exact launch path while ordinary
tickets remain event-free. Three deterministic and one live test cover event
lifetime, ordering, cleanup, and CPU-equal output. Retained evidence under `benchmarks/accelerator/evidence/2026-07-29-independent-ticket-event-timeline-rtx4060/`
uses the same workload SHA and records overlap in 2/15, 8/15, and 15/15 samples for
groups 2/4/8. Median overlap is 0/0.006144/0.015360 ms, median interval concurrency
is 1.000x/1.072x/1.091x, and maximum peak is 2/3/5. This is diagnostic event-interval
attribution, not pure kernel duration, SM occupancy, or kernel-transfer overlap.
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
The shared boundary now also exposes
`validated-search-submission-v1` through `accelerator/search_submission.py`. One
exact algorithm/problem/seed/budget request binds an optional ticket plus deferred
mandatory CPU search. Publication validates capability, algorithm, seed, and
proposal budget; optional cleanup must complete before fallback, malformed tickets
fail closed, and no proposal gains acceptance authority. Ten tests cover deferred
CPU, exact optional publication, submit/wait/result fallback, malformed ticket,
idempotence, close, cached mandatory failure, and cleanup failure.
`classic-rotate-target-search-submission-v1` is the first concrete search-ticket
composition. It retains exact full-batch selector/projection proofs, submits only
the zero-or-one selector-relevant sub-batch through the candidate ticket, and
publishes proposals against the full batch after validation. Eight tests include
three live CUDA routes for one-position exactness, empty projection, and teardown
fallback. No ticket-specific speedup or independent-stream claim follows. The
shared boundary now also exposes
`validated-verification-assist-submission-v1`. Optional assistance publishes only
after exact verifier/capability/order validation and successful ticket cleanup;
absence or clean typed failure completes with no hints, while malformed tickets or
cleanup failure fail closed. Nine tests cover the neutral lifetime.
`candidate-evidence-verification-submission-v1` composes nested candidate tickets
into exact ordered hints while preserving evaluator/verifier identity. Seven tests
include three live CUDA routes for CPU-equal hints and teardown-driven empty
completion. Hints remain optional and untrusted; `TrustedCandidateVerifier` alone
owns acceptance. Crazy-target search now also uses the neutral submission lifetime
through a proof-bound 1,024-item candidate ticket; seven tests cover its exact and
fallback routes. The retained matrix at `benchmarks/accelerator/evidence/2026-07-29-crazy-target-performance-matrix-rtx4060/` records 16.425x CPU prepared,
11.601x CUDA prepared, and 1.270x one-shot CUDA-ticket improvements over their
same-run ordinary baselines, all with 15/15 paired wins; CUDA prepared remains
9.137x faster than the ticket.
Hardware-neutral `evidence-bound-ticket-route-admission-v1` now gives ticket
grouping an explicit evidence gate. It validates exact backend, device, and
workload identity plus exact output, lower candidate median, and a strict
paired-win majority; malformed or duplicate route records fail closed. Plans
preserve input order, minimize chunk count, then measured median cost, and
prefer synchronous ties. Opt-in
`evidence-bound-ticket-route-admission-report-v1` publishes one immutable
assessment per retained route in input order. It distinguishes context
mismatch, inexact results, no median improvement, no paired majority, and a
group larger than the pending queue. Eligible but unused routes remain visible
with zero selected counts; the report also records selected chunks/tickets,
fallback tickets, synchronous/streamed totals, and the unchanged plan. It reads
no additional evidence, performs no online learning, and changes no default.
`bounded-ticket-admission-telemetry-v1` retains completed reports in a
caller-owned positive-capacity FIFO.
`bounded-ticket-admission-failure-telemetry-v1` independently retains failed
accelerator attempts as unavailable, invalid-input, execution, or other stable
categories without exception text. Both immutable snapshots expose monotonic
sequence IDs, eviction counts, measured/estimated duration delta, and exact
selected-route usage. Malformed reports, timings, or foreign failures fail
before mutation. `TicketAdmissionAttemptTelemetry` pairs the two FIFOs, and a
separate retained CUDA attempt executor records exactly one outcome before
returning or re-raising the same accelerator error. The ordinary and existing
completion-only executors remain unchanged.
`ticket-admission-telemetry-document-v1` captures both snapshots as compact,
sorted-key schema-v1 JSON. Decoding defaults to a 1 MiB byte limit and 4,096
observations per FIFO, rejects duplicate, unknown, oversized, and noncanonical
input, and restores exact sequence and eviction state. File reads and writes are
explicit; writes use a same-directory temporary file and atomic replacement.
`caller-owned-ticket-admission-telemetry-store-v1` defines an explicit
put/get/remove/snapshot port and a bounded caller-owned memory adapter.
Defaults are 4,096 unique documents, 4,096 observations per FIFO, and 16 MiB
of exact schema-v1 canonical bytes. Fingerprints
reuse `ticket-admission-telemetry-document-v1:sha256:<hex>`; duplicate puts are
idempotent, limits cannot be widened after construction, snapshots are ordered by
fingerprint, and removal releases exact document and byte budgets. Invalid
fingerprints/documents, budget overflow, collisions, or retained decode failure fail
closed without partial mutation. The memory adapter performs no filesystem I/O,
automatic loading, summaries, merging, recommendations, or admission changes.
`ticket-admission-telemetry-schema-migration-v1` publishes a fixed lossless
1-to-1, 1-to-2, 2-to-1, and 2-to-2 compatibility matrix. Schema-v2 is canonical
sorted JSON containing the exact canonical schema-v1 bytes as standard Base64,
plus the required schema-v1 document identity and SHA-256 fingerprint. Versioned
decoding defaults to 2 MiB outer bytes, 1 MiB embedded source bytes, and 4,096
observations per FIFO. Upgrade and downgrade are explicit; schema-v1 bytes remain
unchanged. There is no automatic migration, file loading, snapshot
reinterpretation, merge, recommendation, lineage inference, or policy change.
`offline-ticket-admission-telemetry-summary-v1` validates one explicit document
and groups retained observations by exact backend, device, workload, and ticket
count. It publishes completed/failed integer totals, estimate-comparison counts,
retention ranges, stable failure categories, and sorted selected-evidence
appearances.
`offline-ticket-admission-telemetry-collection-v1` defaults to explicit
4,096-document and 16 MiB canonical-input bounds. It fingerprints canonical bytes
as `ticket-admission-telemetry-document-v1:sha256:<hex>`, counts byte-identical
occurrences once, publishes input/unique/duplicate byte counts, and orders unique
entries by fingerprint. Different snapshots remain separate even when their
contexts or sequence ranges overlap; digest collisions fail closed.
`offline-ticket-admission-telemetry-overlap-v1` compares two validated documents
in fingerprint order. For completed and failed FIFOs it publishes capacities,
retained half-open sequence ranges, exact overlap ranges, matching counts, and
conflicting sequence IDs, with explicit empty and no-overlap classifications. An
exact document match is separate from matching retained observations.
`offline-ticket-admission-telemetry-overlap-index-v1` deduplicates one bounded
collection before comparing every unique pair. It defaults to a 65,536-pair
budget, fails before pairwise work when that budget is exceeded, orders reports by
fingerprint, and publishes completed/failed counts for all four overlap classes.
Exact duplicates remain collection occurrences and never create pairs.
`offline-ticket-admission-telemetry-overlap-components-v1` selects an undirected
edge only when completed and failed FIFOs contain at least one exact matching
observation in total and neither FIFO has a conflicting sequence ID. It retains
isolated unique documents, fingerprints each component, and publishes member,
direct, possible, and missing edge counts plus a clique flag. A bridged component
may contain member pairs with no direct edge, so connectivity is neither pairwise
equivalence nor recorder lineage. Component fingerprint collisions fail closed.
`authenticated-ticket-admission-telemetry-lineage-v1` separately binds one exact
document fingerprint to caller-supplied recorder, completed/failed stream, capture
sequence, key, and optional immediate-predecessor identities. Canonical
HMAC-SHA-256 uses at least 32 caller-owned secret bytes; the secret is never stored.
Verification requires an explicit trusted key identity and secret. Same-sequence
forks, adjacent predecessor mismatch, nonadjacent direct links, MAC mismatch, and
fingerprint collisions fail closed. Different recorder or stream identities remain
separate lineages; ordered gaps are common lineage without a direct link. The
caller owns key legitimacy.
`caller-owned-ticket-admission-telemetry-lineage-trust-v1` builds an explicit
in-memory set of at most 256 unique HMAC keys, sorted by `key_id`. Each key has an
inclusive first/optional-last capture sequence window; empty sets trust nothing.
Verification selects the exact key identity and window, and independently verified
items may be compared across a rotation. Duplicate identities, malformed windows,
unknown keys, out-of-window captures, and incorrect secrets fail closed. Secret
fields are hidden from representations.
`ticket-admission-telemetry-lineage-trust-manifest-v1` canonically persists only
`key_id`, an opaque `key_reference_id`, and inclusive capture windows. It defaults
to 256 entries and 64 KiB, orders entries by key identity, fingerprints canonical
bytes, and supports only explicit bounded reads and atomic replacement. Resolution
requires exact caller-supplied key/reference coverage and produces manifest-bound
in-memory trust. A resolved secret is not certified until an attestation verifies.
Duplicate keys/references, malformed or noncanonical JSON, incomplete or excessive
coverage, reference mismatch, and storage failures fail closed. Secrets never enter
manifest bytes.
`explicit-ticket-admission-telemetry-lineage-secret-provider-v1` accepts one
caller-supplied synchronous provider. Manifest validation and a default 256-request
budget complete before the first call. Immutable requests follow canonical key
order and carry manifest/provider identity, key/reference identity, capture window,
and request index. Providers return only typed `resolved`, `unavailable`, or
`failed` results; non-success stops without retry, and each entry is called exactly
once. Repeated explicit resolutions call the provider again. Secret bytes remain
hidden, and resolution still does not authenticate them before attestation use.
`caller-owned-ticket-admission-telemetry-lineage-signature-v1` defines
algorithm-neutral synchronous detached signer and verifier ports. Canonical
attestations bind the exact schema-v1 document fingerprint, algorithm, recorder,
completed/failed streams, capture sequence, public-key ID, SHA-256 of the exact
caller-owned public-key bytes, and optional HMAC or signature predecessor. Signers
return typed `signed`, `unavailable`, or `failed`; verifiers return `verified`,
`invalid`, `unavailable`, or `failed`. Each explicit operation calls its port once
without retry or cache. Verification checks the exact public-key fingerprint before
the port call, then reuses the common verified-lineage comparison for public-key
rotation and an explicit HMAC-to-signature transition. No concrete signature
algorithm, key generation, private-key storage, certificate chain, PKI, trust
discovery, provider lifecycle, or security claim is supplied by this boundary.
`caller-owned-ticket-admission-telemetry-lineage-signature-trust-v1` builds
an explicit in-memory set of at most 256 unique `(algorithm_id, public_key_id)`
pairs sorted by that composite identity. Each entry binds exact public-key bytes,
their required SHA-256 fingerprint, and an inclusive first/optional-last capture
window. Empty sets trust nothing. Verification selects the exact algorithm, key
identity, fingerprint, and capture window before calling the verifier; independently
verified items preserve same-key, public-key rotation, algorithm rotation, ordered
gap, and fork checks. Duplicate identities, malformed windows, invalid key bytes,
fingerprint mismatch, unknown identities, out-of-window captures, and tampered
trust metadata fail closed. Public-key bytes are hidden from representations. No
manifest, provider, certificate, PKI, trust discovery, algorithm selection, or
policy authority is supplied.
`ticket-admission-telemetry-lineage-signature-trust-manifest-v1` persists
algorithm identity, public-key identity, one opaque public-key reference, the
required exact public-key fingerprint, and inclusive capture windows as canonical
key-free JSON. It defaults to 256 entries and 64 KiB, sorts by composite identity,
requires globally unique references, publishes a stable SHA-256 fingerprint, and
supports only explicit bounded reads or atomic replacement. Resolution requires
exact caller-supplied algorithm/key/reference coverage and exact public-key bytes
matching the persisted fingerprint before building manifest-bound in-memory
signature trust. The same public-key ID may exist under distinct algorithms.
Duplicate identities or references, malformed or noncanonical JSON, incomplete or
excessive coverage, reference or fingerprint mismatch, and storage failures fail
closed. No public-key bytes, provider, certificate, PKI, trust discovery, algorithm
selection, or policy authority are supplied.
`explicit-ticket-admission-telemetry-lineage-public-key-provider-v1` accepts one
caller-supplied synchronous provider. It validates the signature trust manifest and
a default 256-request budget before the first call, then emits immutable requests
in canonical `(algorithm_id, public_key_id)` order. Each request carries only the
manifest/provider identities, algorithm/key/reference identities, required exact
public-key fingerprint, capture window, and request index. Providers return typed
`resolved`, `unavailable`, or `failed` results. Each entry is called exactly once;
non-success stops without retry, while repeated explicit resolution performs a
fresh provider walk. Resolved bytes are hidden from representations and must match
the manifest fingerprint before in-memory signature trust is constructed. No
provider discovery, built-in key service, retry, cache, persistence, hidden worker,
certificate validation, PKI, algorithm selection, or policy authority is supplied.
`explicit-async-ticket-admission-telemetry-lineage-public-key-provider-v1`
accepts one caller-supplied async provider and reuses the synchronous request,
result, and resolved-trust contracts. The caller owns and starts the coroutine and
event loop. Manifest, provider identity, and the default 256-request budget are
validated before the first provider await. Requests are awaited sequentially in
canonical `(algorithm_id, public_key_id)` order, with no task creation or hidden
parallelism; each entry is awaited exactly once and repeated explicit resolution
performs a fresh walk. Typed non-success stops without retry. Ordinary provider
exceptions become stable boundary errors without vendor text, while cancellation
propagates to the caller. Exact public-key fingerprints are checked before trust
construction. This sequential port creates no event loop, task, provider session,
concurrency policy, discovery, retry, cache, persistence, certificate validation,
PKI, algorithm selection, or admission authority.
`explicit-async-batch-ticket-admission-telemetry-lineage-public-key-provider-v1`
accepts one caller-supplied async batch provider. Manifest, provider identity, and
the default 256-request budget are validated before the first await. Empty manifests
make no provider call; nonempty manifests produce one immutable batch containing the
full canonical `(algorithm_id, public_key_id)` request tuple and exactly one provider
await. The provider owns all scheduling and may resolve the batch sequentially or
concurrently. The boundary requires one exact positional result tuple with matching
cardinality, validates every shared typed item result, propagates cancellation, and
converts ordinary provider exceptions to stable errors without vendor text. Reversed,
missing, excessive, foreign, nonresolved-with-bytes, or fingerprint-mismatched results
fail closed before trust is returned. This batch port creates no event loop, task,
concurrency implementation, provider session, discovery, retry, cache, persistence,
certificate validation, PKI, algorithm selection, or admission authority.
`explicit-async-session-ticket-admission-telemetry-lineage-public-key-provider-v1`
accepts one caller-supplied async lifecycle port around the batch provider. Manifest,
provider identity, and the default 256-request budget are validated before opening.
Empty manifests perform no lifecycle calls. Nonempty manifests call `open` exactly
once with immutable manifest fingerprint, provider identity, and request count;
typed outcomes are `opened`, `unavailable`, or `failed`, and only `opened` may carry
a hidden callable batch provider. The existing canonical batch boundary then runs
once. Every opened session receives exactly one `close` request with a stable
`completed`, `failed`, or `cancelled` reason; close outcomes are `closed` or
`failed`. Opening exceptions become stable errors without vendor text and opening
cancellation propagates without closing. After opening, failure or cancellation
attempts one close. Cancellation propagates only after successful close; close
failure replaces the preceding outcome and fails closed. No built-in service,
event loop, task, discovery, retry, cache, persistence, certificate validation,
PKI, algorithm selection, or admission authority is supplied.
`bounded-in-memory-ticket-admission-telemetry-lineage-public-key-provider-v1`
implements the synchronous provider port with one caller-owned immutable key tuple.
Construction accepts at most 256 entries, validates canonical provider, algorithm,
key, and reference identities, validates inclusive capture windows, recomputes every
exact public-key SHA-256 fingerprint, rejects duplicate composite identities and
references, and sorts entries by reference identity. Key bytes are hidden from
representations. Every explicit lookup revalidates service identity, count, tuple,
ordering, metadata, and exact key bytes. An absent reference returns typed
`unavailable`; a known reference with different algorithm, key, fingerprint, or
window returns typed `failed`; only an exact request returns `resolved`. Empty
services are valid and resolve nothing. The object is reusable caller-owned memory,
not an automatic or hidden cache. It performs no file, environment, network,
discovery, mutation, retry, persistence, async adaptation, certificate validation,
PKI, algorithm selection, or admission-policy operation.
`bounded-in-memory-async-ticket-admission-telemetry-lineage-public-key-provider-v1`
adapts one exact bounded memory service to the sequential async provider port.
Construction validates the complete wrapped service and retains only its provider
identity, key count, stable adapter identity, and a hidden service reference. Every
await revalidates the adapter binding and the complete memory service before invoking
the synchronous lookup inline. It returns the same typed `resolved`, `unavailable`,
or `failed` outcome and introduces no internal suspension point; the caller-owned
event loop cannot run another task merely because this adapter was awaited. The
existing sequential async boundary still performs manifest preflight, canonical
ordering, fingerprint checks, stable exception wrapping, and trust construction.
Empty manifests perform no lookup, while explicit adapter construction already
validates the service. The adapter creates no event loop, task, sleep, artificial
yield, batch/session lifecycle, file, environment, network, discovery, retry,
persistence, certificate validation, PKI, algorithm selection, or policy operation.
`bounded-memory-async-batch-ticket-admission-telemetry-lineage-public-key-provider-v1`
adapts one exact bounded memory service to the caller-controlled async batch port.
Construction validates the complete wrapped service and a positive request limit of
at most the caller-selected boundary, defaulting to 256. Every await revalidates the
adapter binding and complete memory service, then validates the exact batch request,
nonempty manifest/provider identities, immutable request tuple, configured count,
positional indices, and every item manifest/provider binding. Requests are resolved
inline in tuple order through the synchronous memory service and returned as one
hidden positional result tuple, preserving typed `resolved`, `unavailable`, and
`failed` outcomes. Direct empty batches are valid. The existing batch trust boundary
still performs manifest preflight, one nonempty provider await, exact cardinality and
fingerprint checks, and trust construction; empty manifests make no provider call.
The adapter creates no event loop, task, concurrency, sleep, artificial yield,
session lifecycle, file, environment, network, discovery, retry, persistence,
certificate validation, PKI, algorithm selection, or policy operation.
`memory-async-session-ticket-admission-telemetry-lineage-public-key-provider-v1`
adapts one exact bounded memory service to the explicit async provider-session port.
Construction validates the memory service, builds its bounded inline batch adapter,
and stores only caller-owned serial lifecycle state. `open` and `close` complete
inline without scheduling. One active lifecycle is allowed: an exact nonempty open
request with matching provider identity and bounded request count returns `opened`
with the hidden memory batch adapter; a second or mismatched open returns `failed`
without replacing active state. Close requests require the exact persisted manifest
fingerprint, provider identity, and request count. A mismatch returns `failed` and
retains active state; an exact close returns `closed`, clears the active request,
increments a nonnegative completed-lifecycle count, and permits serial reuse. The
existing session boundary still preflights manifests and budgets, performs no
lifecycle calls for empty manifests, and closes after success or batch failure. The
adapter creates no event loop, task, lock, concurrency, sleep, artificial yield,
file, environment, network, discovery, retry, persistence, certificate validation,
PKI, algorithm selection, or policy operation.
`ticket-admission-telemetry-lineage-public-key-bundle-v1` persists one explicit
bounded public-key service as canonical compact UTF-8 JSON. Unlike the key-free
trust manifest, this separate document intentionally contains public-key bytes as
lowercase hexadecimal. Construction reuses the memory provider to validate exact
bytes, fingerprints, identities, windows, uniqueness, cardinality, and reference
ordering. Encoding uses sorted keys and one trailing newline; decoding requires byte
identity with that canonical encoding, rejects duplicate or unknown JSON keys, and
is bounded by 256 entries and 1 MiB by default. Explicit writes atomically replace
one caller-selected path. Explicit reads consume at most the configured byte limit.
Each explicit load rereads the path, fingerprints canonical bytes, and builds a new
caller-owned memory provider with hidden key material and stable non-key metadata.
There is no path discovery, automatic loading, watch, retained cache, retry, network
fetch, session creation, certificate validation, PKI, algorithm selection, or policy
operation.
`explicit-ticket-admission-telemetry-lineage-public-key-bundle-fetcher-v1`
defines one synchronous transport-neutral fetch boundary. The caller constructs an
exact immutable request binding source identity, resource identity, provider
identity, expected bundle fingerprint, byte limit, and entry limit. All request
metadata and limits are validated before the first transport call. Each invocation
makes exactly one caller-supplied fetcher call and accepts only the exact typed
`fetched`, `unavailable`, or `failed` result enum. Nonfetched results cannot carry
bytes. A fetched result requires exact nonempty bytes within the requested limit,
canonical bundle decoding, a newly materialized caller-owned memory provider, and
exact matches for the expected bundle fingerprint and provider identity. Repeated
explicit invocations call the transport again and retain no cache. The boundary
implements no HTTP, TLS, endpoint discovery, credential handling, redirect, retry,
watch, persistence, certificate validation, PKI, algorithm selection, or policy
operation.
`explicit-async-ticket-admission-telemetry-lineage-public-key-bundle-fetcher-v1`
defines the caller-driven async form of the same transport-neutral boundary. The
caller owns the coroutine and event loop. The exact shared request is completely
validated before the first await, and each invocation awaits the supplied fetcher
exactly once. The shared typed result, bounded canonical decode, fingerprint and
provider bindings, and caller-owned memory-provider materialization remain the
single synchronous source of validation truth. Ordinary fetcher exceptions become
stable async-boundary errors without vendor text, while cancellation propagates
directly. Repeated explicit invocations await the transport again and retain no
cache. The boundary creates no event loop, task, worker, concurrency policy,
endpoint discovery, credential handling, redirect, retry, watch, persistence,
certificate validation, PKI, algorithm selection, or policy operation.
`explicit-https-ticket-admission-telemetry-lineage-public-key-bundle-fetcher-v1`
implements one concrete synchronous stdlib HTTPS GET transport. Its exact immutable
config binds a canonical lowercase ASCII host, TCP port, origin-form target,
source/resource identities, a positive finite timeout capped at 300 seconds, and a
caller-owned `SSLContext`. Build and every use require hostname checking,
`CERT_REQUIRED`, and TLS 1.2 or newer; the module never creates or loads trust roots.
Each invocation revalidates the config and shared fetch request, requires exact
source/resource matches, opens one new `HTTPSConnection` with the same caller
context, sends only `GET` with JSON/identity/close headers and no credentials, and
closes once. Status 200 may return `fetched`; 404 and 410 return `unavailable`; all
other statuses, including redirects, return `failed`. Successful responses require
JSON content type with optional UTF-8 charset, absent or identity content encoding,
an optional canonical positive content length within the request limit, and an exact
nonempty bytes body read with a `max_bytes + 1` bound. Connection, request, response,
body-read, or close failures return typed `failed` without vendor text. There is no
plaintext HTTP, endpoint discovery, credential handling, redirect following, retry,
watch, cache, persistence, hosted-service API, certificate/PKI ownership, algorithm
selection, or policy operation.
`offloaded-async-https-ticket-admission-lineage-public-key-bundle-fetcher-v1`
adapts the exact synchronous HTTPS fetcher to the shared async port through one
caller-supplied offloader. Construction and every call fully revalidate the wrapped
HTTPS fetcher, stable adapter identity, copied fetcher/source/resource bindings, and
callable offloader. The shared request is validated before the first await; a
source/resource mismatch returns typed `failed` without calling the offloader. A
matched request awaits the offloader exactly once with the same exact fetcher and
request. The caller alone decides whether that await runs inline, in a thread,
through an executor, or through another scheduling mechanism. Cancellation
propagates directly. Ordinary offloader exceptions become stable adapter errors
without vendor text. Returned results are revalidated for exact type, enum, payload
presence, exact bytes, nonempty content, and the request byte limit before they reach
the outer async materialization boundary. Repeated calls revalidate and offload
again. The adapter creates no event loop, task, thread, executor, worker, retry,
redirect, cache, trust root, credential, hosted-service policy, algorithm choice, or
admission-policy operation.
`explicit-ticket-admission-lineage-https-authorization-provider-v1`
defines one synchronous caller-owned port for resolving an opaque HTTPS
`Authorization` value. Preflight validates the exact HTTPS fetcher, exact canonical
bundle-fetch request, source/resource binding, canonical authorization-provider
identity, callable provider, and positive byte limit before the provider is called.
The default limit is 4096 ASCII bytes and the supported maximum is 16384. One
immutable request carries only the bundle fingerprint and nonsecret provider,
resource, and source identities. Each successful preflight makes exactly one
provider call. Stable `resolved`, `unavailable`, and `failed` outcomes carry no
vendor text; nonresolved outcomes cannot carry credential text. A resolved value
must be exact nonempty ASCII field text containing only spaces and visible
characters, with no edge spaces and no normalization. The value is hidden from
representations and returned only in caller-owned state with its exact byte count
and the fixed `Authorization` header name. Repeated explicit resolutions call the
provider again. The port does not choose an authorization scheme, inject a header,
open a connection, discover credentials, retry, cache, persist, log values, create
workers, own a hosted-service API, validate certificates, distribute PKI, select a
signature algorithm, or change admission policy.
`explicit-async-ticket-admission-lineage-https-authorization-provider-v1`
defines one caller-driven async port for resolving the same bounded opaque HTTPS
`Authorization` value. The synchronous port now exposes one immutable nonsecret
preflight plus one exact result materializer, and both sync and async resolution use
those same validators. Preflight validates the exact HTTPS fetcher, canonical bundle
request, source/resource binding, authorization-provider identity, and positive byte
limit before the first `await`; a noncallable provider also fails before awaiting.
One successful preflight awaits the caller-supplied provider exactly once with the
same exact immutable request. The provider controls whether that await suspends.
Cancellation propagates directly. Ordinary provider exceptions become stable async
errors without vendor text. The shared materializer enforces exact result type and
enum, forbids credential text in nonresolved outcomes, requires bounded nonempty
ASCII field text for `resolved`, and returns the same hidden caller-owned metadata as
the synchronous path. Repeated explicit resolutions await again with no cache or
refresh. The port creates no event loop, task, thread, executor, worker, retry,
discovery, refresh, header injection, hosted-service policy, certificate rule, PKI
operation, algorithm choice, or admission-policy operation.
`memory-ticket-admission-lineage-https-authorization-provider-v1`
implements one reusable bounded caller-owned synchronous Authorization provider over
explicit immutable in-memory entries. Each entry binds one hidden Authorization
value and exact byte count to one canonical bundle fingerprint, fetch-provider
identity, resource identity, and source identity. One service binds all entries to
one authorization-provider identity, permits at most 64 entries by default and 4096
at the supported maximum, requires canonical deterministic ordering, and rejects
duplicate request bindings. Construction and every call revalidate the exact service
type and identity, provider identity, limits, entry tuple, shared request metadata,
shared Authorization text rules, byte counts, ordering, and uniqueness. A request
with a different authorization-provider identity returns typed `failed`; a valid
unmatched request returns `unavailable`; an exact match returns `resolved` with the
unchanged hidden caller-owned value. Repeated calls perform the same validation and
lookup without mutation or an external cache. The provider reads no environment,
file, network, process credential state, secret store, or hosted API and performs no
discovery, refresh, retry, persistence, logging, task creation, certificate rule,
PKI operation, algorithm choice, or admission-policy operation.
`memory-async-ticket-admission-lineage-https-authorization-provider-v1`
adapts one exact bounded memory Authorization provider to the shared async provider
port without introducing a scheduling point. Construction and every call revalidate
the exact adapter type and identity, wrapped memory service, copied entry count,
entry limit, and authorization-provider identity. A direct await delegates once to
the same synchronous memory lookup and returns the same typed `resolved`,
`unavailable`, or `failed` result before any other caller task can run. The shared
async Authorization boundary can therefore materialize the exact hidden value and
metadata while preserving its own preflight and result validation. Repeated awaits
reuse only the explicit immutable memory state and perform validation again. The
adapter creates no event loop, task, thread, executor, worker, scheduling point,
environment or file read, network access, secret-store call, discovery, refresh,
retry, external cache, persistence, logging, hosted-service policy, certificate
rule, PKI operation, algorithm choice, or admission-policy operation.
`authorized-https-ticket-admission-lineage-public-key-bundle-fetcher-v1`
binds one exact synchronous HTTPS fetcher to one exact caller-owned resolved
Authorization value. Construction and every call revalidate the wrapped HTTPS
fetcher, resolved Authorization value, stable adapter identity, copied byte count,
authorization-provider identity, bundle fingerprint, fetch-provider identity, and
source/resource bindings. A request must exactly match the bound bundle fingerprint,
fetch provider, source, and resource; any mismatch returns typed `failed` before a
connection is opened. A matched call opens one connection, sends one `GET` with the
base JSON/identity/close headers plus exactly one unchanged `Authorization` header,
reuses the base response/status/body validation, and closes once. The explicit
adapter may be reused with the same caller-owned authorization object, but it never
calls a credential provider, refreshes credentials, retries, redirects, caches
hidden state, normalizes or selects a scheme, logs credential text, discovers an
endpoint, creates workers, owns a hosted-service API, validates certificates,
distributes PKI, selects a signature algorithm, or changes admission policy.
`offloaded-async-authorized-https-ticket-admission-lineage-key-bundle-fetcher-v1`
adapts one exact authorized synchronous HTTPS fetcher to the shared async fetch port
through one caller-supplied offloader. Construction and every call fully revalidate
the wrapped authorized fetcher, stable adapter identity, copied authorization byte
count, authorization-provider identity, bundle fingerprint, fetch-provider identity,
and source/resource bindings. The shared request is validated before the first
`await`; any fingerprint/provider/source/resource mismatch returns typed `failed`
without invoking the offloader. A matched request awaits the offloader exactly once
with the same exact authorized fetcher and request, then revalidates the exact typed
result and request byte limit. The caller alone decides whether blocking work runs
inline, in a thread, through an executor, or by another scheduling mechanism.
Cancellation propagates directly. Ordinary offloader exceptions become stable
adapter errors without vendor text. Repeated calls offload again but never resolve or
refresh credentials. The adapter creates no event loop, task, thread, executor,
worker, retry, redirect, cache, trust root, credential provider, hosted-service
policy, certificate rule, PKI operation, algorithm choice, or admission-policy
operation.
The built-in public-key implementations are the bounded caller-owned memory
service, its inline sequential and batch async adapters, its serial session
adapter, explicit canonical file bundles, synchronous plus async
transport-neutral fetch ports, a concrete synchronous HTTPS GET adapter,
a caller-offloaded async HTTPS adapter, explicit synchronous and async
Authorization-provider ports, a bounded caller-owned memory Authorization
provider with an inline async adapter, an explicit authorized HTTPS adapter,
and a caller-offloaded async
authorized HTTPS adapter. There is no built-in environment, file, external
secret-store, or hosted credential provider, native nonblocking HTTPS client,
automatic credential refresh, or hosted key service.
No bundle or session is loaded automatically;
there is no discovery, retry,
retained cache, persistence, automatic trust
loading, snapshot merge, route recommendation, or policy authority. There is no
hidden worker or
automatic promotion. The retained
`rtx4060-full-domain-crazy-ticket-admission-2026-07-29-v1` profile binds the RTX
4060 `sm_89` capability and full-domain CRAZY workload to source commit
`431f542ab6321eeb12b7bcb9195318f25cf376a5`. It admits synchronous groups 2/4/8
and rejects streamed routes 1/2/4/8; a ten-ticket queue therefore selects groups
2+8 at a 7.3271 ms estimated median. The opt-in executor validates the packed
workload SHA-256, reverse-waits each group, restores input order, and closes
every ticket. One thousand two hundred seventy-three
admission/telemetry/persistence/store/migration/summary/collection/overlap/
index/components/lineage/trust/manifest/provider/signature/signature-trust/
signature-manifest/public-key-bundle/public-key-bundle-fetcher/
async-public-key-bundle-fetcher/https-public-key-bundle-fetcher/
async-https-public-key-bundle-fetcher/https-authorization-provider/
async-https-authorization-provider/
memory-https-authorization-provider/
memory-async-https-authorization-provider/
authorized-https-public-key-bundle-fetcher/
async-authorized-https-public-key-bundle-fetcher/
public-key-provider/async-public-key-provider/
async-batch-public-key-provider/provider-session/
memory-public-key-provider/memory-async-public-key-provider/
memory-batch-public-key-provider/
memory-session-public-key-provider tests cover fallback,
positive/negative
evidence, duplicate/malformed records, exact profile matching, seven isolated
runtime drifts, multi-profile selection, invalid/unknown workloads, ambiguity, and
three live CUDA routes. The seven route records and exact
provenance now live in schema-v4
`accelerator/cuda/ticket_admission_profiles.json`, not Python source.
`benchmarks/accelerator/ticket_admission_profile_manifest.py` reconstructs those
canonical bytes from retained JSON/TOML, source commit, exact raw/structured-output
hashes, the tracked CUDA toolchain manifest, retained driver build, and retained
host/Python context. Twelve manifest tests require byte equality and reject
duplicate or unknown keys, unsupported schema, duplicate routes, malformed display
versions, invalid host fields, exact runtime-context duplicates, and direct
capability/runtime mismatch; distinct runtime variants may coexist for one
capability/workload. Runtime loading reads only the tracked product manifest and
never opens benchmark evidence. `resolve_cuda_ticket_admission_profile` selects at
most one exact workload/capability/runtime record; invalid or ambiguous requests
fail closed, while retained wrappers delegate through the stable workload identity. At adapter
startup, `cuda-runtime-toolchain-identity-v1` requires Driver API 13030 or newer,
exact NVRTC 13.3, the tracked toolchain SHA-256, and NVML display build `610.88`;
`cuda-host-runtime-identity-v1` measures Windows 11 Professional build
`10.0.26200`, `x86_64`, and CPython `3.14.6`. Missing or failed optional NVML or
host measurement leaves ordinary CUDA available but this evidence-bound profile
unmatched. Fourteen runtime-identity tests cover required query/hash failures,
NVML lifetimes, host validation, exact live host measurement, and one live CUDA
route. Other hosts, Python versions, driver builds, devices, and workloads remain
open. The global synchronous default does not change.
Other CUDA/ROCm strategies, event-instrumentation controls, additional
admission profiles, and other kernel/callback workloads remain open.

## Invariants

- Compiler/verifier code depends on a hardware-neutral capability contract;
  CUDA/ROCm/CPU adapters can be substituted without changing compiler semantics
  or candidate validity rules.
- A CPU/reference path remains sufficient for correctness, and accelerator
  failure/unavailability changes performance rather than semantic acceptance.

## Failure Behavior

Missing hardware, resource exhaustion, or accelerator disagreement falls back or
fails explicitly without changing correctness rules.

## Verification

- Expected durable artifact surface: `accelerator/`, `algorithms/`,
  `optimizer/`, `benchmarks/accelerator/`, `tests/optimizer/`.
- `tests/optimizer/test_exact_accelerator_primitives.py` checks CPU known edges,
  malformed shared requests, CUDA lifecycle failure, and CPU/CUDA differential
  equality over boundary values plus deterministic 4,096-element corpora.
- Current development GPU evidence identifies an NVIDIA GeForce RTX 4060 as
  `sm_89`. Performance matrices are retained separately from correctness evidence
  and do not establish a CPU-relative or cross-device speedup.
- `tests/vm/cuda_step.rs` checks compact transition results against normative
  Rust traces across every instruction family and adversarial transition edges.
- `tests/vm/cuda_run.rs` checks complete resident classic bounded-run results,
  including every final memory word, against normative Rust.
- `tests/vm/cuda_profile_run.rs` checks eight complete current-profile outcomes,
  including every one of the 4,782,969 final memory words, against normative Rust.
- A live synthetic five-trit/243-word CUDA test proves resident kernel generation
  is geometry-driven rather than fixed to the published 10/14-trit profiles.
- `tests/vm/batch_backend.rs` proves whole-batch unavailability, malformed
  backend shape, per-item deferral, and complete checkpoint restoration all fall
  back deterministically to safe Rust, while preserving exact per-item execution
  origin. CUDA integration tests exercise the same product ports against the real
  resident workers and fail if the worker runs but no backend completion is
  accepted.
- Current-profile post-optimization evidence is retained under
  `benchmarks/accelerator/evidence/2026-07-27-current-profile-resident-session-rtx4060/`.
- Resident snapshot phase evidence is retained under
  `benchmarks/accelerator/evidence/2026-07-28-current-profile-resident-snapshot-phase-profile-rtx4060/`.
- Caller-owned snapshot workspace evidence is retained under
  `benchmarks/accelerator/evidence/2026-07-28-current-profile-snapshot-workspace-tradeoff-rtx4060/`.
- Bounded host-registration evidence is retained under
  `benchmarks/accelerator/evidence/2026-07-28-current-profile-snapshot-host-registration-tradeoff-rtx4060/`.
- Bounded streamed-snapshot window evidence is retained under
  `benchmarks/accelerator/evidence/2026-07-29-current-profile-snapshot-stream-window-tradeoff-rtx4060/`.
- Registered double-buffer snapshot evidence is retained under
  `benchmarks/accelerator/evidence/2026-07-29-current-profile-snapshot-double-buffer-overlap-rtx4060/`. Matched windows 1/8 improve
  1.003x/1.012x with 14/15 and 15/15 paired wins while doubling retained host
  memory; exact synchronous fallback remains authoritative.
- `tests/optimizer/test_cuda_ordered_dtoh_stream.py` provides live RTX 4060
  evidence for exact ordered async D-to-H copies, same-host submission order,
  registered-buffer lifetime, invalid ownership rejection, and deterministic
  explicit/runtime teardown.
- `tests/optimizer/test_accelerator_work_ports.py` verifies CPU fallback,
  malformed optional-result fallback, stable algorithm/seed/budget identity,
  optional verification hints, and verifier-only candidate admission.
- `tests/optimizer/test_accelerator_submission.py` verifies the stable neutral
  identity, deferred CPU execution, exact optional publication, idempotent wait,
  typed submit/wait fallback, malformed-ticket rejection, result-shape fallback,
  close-before-wait, mandatory-failure caching, and cleanup-failure rejection.
- `tests/optimizer/test_cuda_independent_kernel_launch.py` verifies both stable
  launch identities, distinct nonblocking handles, stream-specific reverse wait,
  launch-failure destruction, and sync-failure best-effort destruction.
- `tests/optimizer/test_cuda_candidate_submission.py` verifies seven live CUDA
  ticket routes covering exact rotate/crazy publication, empty/idempotent work,
  close-before-wait, teardown fallback, and reverse waiting of two isolated streams.
- `tests/optimizer/test_search_submission.py` verifies stable neutral search
  identity, deferred CPU work, exact optional publication, submit/wait/result
  fallback, malformed-ticket rejection, idempotent completion, close-before-wait,
  mandatory-failure caching, and cleanup-failure rejection.
- `tests/optimizer/test_rotate_target_submission.py` verifies the stable projected
  strategy identity, zero/one exact sub-batches, nested protocol failure, and three
  live CUDA routes covering exact publication, empty work, and teardown fallback.
- `tests/optimizer/test_crazy_target_search.py` verifies the shared normative trit
  table, canonical problem identity, fixed-accumulator packed batches, exact
  multiposition projection, full 59,049-member authority with 1,024 preimages,
  ordinary/prepared equality, forged/failing evidence, trusted admission, and live
  CPU/CUDA equality at resident cardinality 1,024.
- `tests/optimizer/test_crazy_target_submission.py` verifies the stable ticket
  identity, exact 1,024-item nested subset, empty work, malformed evidence/ticket
  handling, live CUDA publication, and teardown-driven CPU fallback.
- `tests/optimizer/test_search_cli.py` additionally verifies crazy-target CPU and
  CUDA registration plus deterministic CUDA-setup fallback.
- `benchmarks/accelerator/evidence/2026-07-29-crazy-target-performance-matrix-rtx4060/` retains 75 chronological samples, Benchmark Protocol v1 metadata,
  an Experiment Manifest v1 run, exact 59,049/1,024 proof identity, CPU/CUDA
  prepared session counters, one-shot ticket identity, proposal equality, and
  independent CPU admission. Medians improve 16.425x CPU prepared, 11.601x CUDA
  prepared, and 1.270x CUDA ticket over same-run ordinary routes.
- `benchmarks/accelerator/evidence/2026-07-29-independent-ticket-stream-throughput-rtx4060/` retains 90 chronological samples, workload/launch/storage identity,
  exact independent CPU bytes for every ticket, and groups 2/4/8. Grouped routes
  improve 1.362x/1.201x/1.322x with 15/15 paired wins. That bundle itself has no
  event attribution; the companion timeline evidence below owns it.
- `tests/optimizer/test_cuda_independent_ticket_transfers.py` verifies exact
  same-stream H-to-D/kernel/D-to-H ordering, host-lease protection, and partial-
  failure cleanup without hardware. Live candidate tests additionally reject
  synchronous copies, preserve crazy output, reverse wait, and teardown fallback.
- `benchmarks/accelerator/evidence/2026-07-29-independent-ticket-transfer-throughput-rtx4060/`
  retains 210 chronological samples across 14 routes. Streamed grouped reaches
  only 0.436x/0.478x/0.494x versus synchronous grouped for groups 2/4/8 and loses
  0/15 paired samples at every group, so synchronous copies remain default.
- `tests/optimizer/test_cuda_independent_ticket_transfer_timeline.py` verifies
  four-marker upload/kernel/download ordering, active-lifetime rejection,
  failed-kernel cleanup, exact event destruction, and one live CPU-equal phase route.
- `benchmarks/accelerator/evidence/2026-07-29-independent-ticket-transfer-event-timeline-rtx4060/`
  retains 45 chronological observations and 210 ticket phase rows. Groups 2/4/8
  record 0.000000 ms median transfer/kernel overlap and 0/15 significant samples;
  group eight records 1.885632 ms summed device phases versus 12.9495 ms wall time.
- `tests/optimizer/test_cuda_independent_kernel_timeline.py` verifies event-origin
  setup, active-lifetime rejection, submission-order samples, synthetic overlap,
  launch-failure cleanup, and one live exact route.
- `benchmarks/accelerator/evidence/2026-07-29-independent-ticket-event-timeline-rtx4060/` retains 45 group observations and 210 intervals with exact shared
  workload identity. Groups 2/4/8 overlap in 2/15, 8/15, and 15/15 samples; group
  eight records 0.015360 ms median overlap, 1.091x median interval concurrency, and
  observed peak five.
- `tests/optimizer/test_ticket_admission.py` verifies stable generic/profile/workload
  identities, singleton fallback, positive synchronous grouping, negative streamed
  rejection, synchronous tie-breaking, context isolation, malformed/duplicate
  evidence failure, exact multi-runtime registry selection, unknown/invalid workload
  rejection, ambiguity failure, exact RTX 4060 queue composition, one live CPU-equal
  executor route, and live wrong-workload rejection.
- `accelerator/cuda/ticket_admission_profiles.json` is the schema-v4 product
  registry generated from retained transfer-throughput evidence, the tracked CUDA
  toolchain manifest, display-driver build, and host/Python context. Runtime loading
  never reads benchmark evidence.
- `tests/optimizer/test_cuda_ticket_admission_profile_manifest.py` verifies
  generated/tracked byte equality, exact commit/hash/runtime provenance,
  admitted-route shape, duplicate JSON keys, unknown root keys, unsupported schema,
  duplicate route identity, malformed display-driver versions, invalid host fields,
  distinct runtime variants, duplicate exact runtime contexts, and direct
  capability/runtime mismatch.
- `tests/optimizer/test_cuda_runtime_identity.py` verifies stable CUDA and host
  protocols, fake Driver API/NVRTC/hash success, required query failures,
  missing-manifest/NVML behavior, NVML lifetimes, invalid host text, exact live host
  measurement, and one live Driver API 13030+/NVRTC 13.3/toolchain-hash/display-
  build/Windows-CPython route.
- `tests/optimizer/test_verification_submission.py` verifies optional deferred
  empty completion, exact publication, submit/wait/result outcomes, malformed-ticket
  rejection, idempotence, close-before-wait, and cleanup-failure caching.
- `tests/optimizer/test_evidence_verification_submission.py` verifies exact nested
  candidate evidence, verifier identity, malformed nested lifetime/result handling,
  and three live CUDA routes for exact hints and teardown-driven empty completion.
- Remaining evidence includes other CUDA/ROCm search and hint tickets, ROCm
  candidate tickets and VM substitution, instrumentation controls, additional
  device/workload admission profiles, broader hardware evidence, and matched
  measurements for other workloads.
- Prerequisite completion evidence: `batch-vm-execution`,
  `compiler-algorithm-experimentation-platform`.
## References

### Host Architecture Baseline

- `docs/technical/adr/host-cpu-and-accelerator-runtime-baseline.md`

- [Replaceable Accelerator And Algorithm
  Ports](../../adr/replaceable-accelerator-and-algorithm-ports.md)
- [Verification Trust Boundary](../../adr/verification-trust-boundary.md)

### Governing ADR Paths

- `docs/technical/adr/replaceable-accelerator-and-algorithm-ports.md`
- `docs/technical/adr/verification-trust-boundary.md`
