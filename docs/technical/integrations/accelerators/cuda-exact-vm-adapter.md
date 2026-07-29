# CUDA exact VM adapter

## Status

Active

## Purpose

Implement the first GPU adapter with exact discrete Malbolge semantics and
massively parallel independent VM execution for candidate evaluation and test
batches.

## Scope

This document governs the following declared TODO scope:

- `accelerator/`
- `algorithms/`
- `optimizer/`
- `benchmarks/accelerator/`
- `tests/optimizer/`

## Current Behavior

### Active Model

CUDA is an optional implementation of hardware-neutral accelerator requests. It
never defines VM semantics or compiler/verifier acceptance. The CPU reference
remains available without GPU execution and supplies differential correctness
evidence.

### Implementation Status

The first exact CUDA slice is implemented for classic ten-trit `rotate` and
`crazy` batches. Integer-only kernels under `accelerator/cuda/` compile at runtime
with NVRTC for the selected device architecture and execute through the CUDA
Driver API. The adapter uses synchronous copies/launches deliberately in this
correctness-first slice; streams, overlap, and throughput tuning remain future
performance work.

Windows x86-64 development pins CUDA 13.3 Update 1 under ignored
`.dependencies/cuda/13.3.1/`. `accelerator/cuda/toolchain.json` records the exact
NVIDIA redistributable paths, component versions, archive sizes, and SHA-256
values. The active adapter binds the reviewed NVRTC/Driver subset directly with
standard-library `ctypes`; it has no additional Python package dependency. CUDA
handles and argument lifetimes stay encapsulated inside `accelerator/cuda/`, and
kernel-parameter owners remain alive through synchronized launch completion.

Development execution on an NVIDIA GeForce RTX 4060 reports `sm_89` and matches
the independent CPU scalar implementation for boundary-heavy and deterministic
4,096-element `rotate`/`crazy` batches.

A compact classic-step adapter is now active as the first VM-semantic CUDA slice.
`ClassicStepRequest` supplies registers, I/O counters, optional next input byte,
and at most four explicitly keyed memory cells. One CUDA thread evaluates one
specification-mode classic transition and returns status/termination/error,
fetched/decoded bytes, committed I/O, final registers/counters, and at most two
actual memory writes. Missing required cells fail as an invalid compact request;
there is no implicit read from undeclared guest memory.

`tests/vm/cuda_step.rs` does not trust a Python CPU clone. It runs the normative
safe-Rust `Machine::step_traced()` first, projects the resulting `StepTrace` to a
fixed-width versioned process protocol, invokes the CUDA worker externally, and
requires exact equality for fourteen fixtures spanning all seven instructions,
no-op, EOF, non-graphical termination, rejected jump atomicity, pointer wrap,
data/self-encryption aliasing, and already-terminated state.

Resident classic execution is now active through the hardware-neutral
`ClassicRunRequest`/`ClassicRunResult` contract. Each request contains the complete
59,049-word memory image, registers, deterministic input, prior output, termination
state, and an explicit bounded step budget. One CUDA thread owns one independent
memory image in device memory and loops over the complete semantic transition
function without host state transfers between steps. The kernel preserves atomic
rejection: a failing self-encryption step contributes no register, I/O, or memory
mutation, while earlier committed steps remain visible.

`tests/vm/cuda_run.rs` serializes complete states to a binary CUDA worker and
requires byte-exact agreement with normative Rust across nine fixtures, including
budget exhaustion, input/output/halt, EOF, non-graphical termination, resumed and
already-terminated execution, rejected jump atomicity, pointer wrap, and
data/encryption aliasing. Every one of the 59,049 memory words is compared. CUDA
unavailability keeps this optional path unavailable rather than changing VM
correctness.

Resident allocations are now budgeted from live driver evidence rather than a
fixed batch constant. `cuMemGetInfo_v2` supplies current free/total bytes and
`cuDeviceGetAttribute` supplies multiprocessor count and maximum threads per
block. The hardware-neutral planner reserves the larger of 8 MiB or 1/16 of total
memory, preserves request order across automatically split chunks, and rejects
any request that cannot fit alone before allocation. There is no configured VRAM
ceiling: backend-specific integer/addressing limits cause additional chunks rather
than rejection or truncation.

Scalable resident execution is active through `ProfileRunGeometry` and the
`ProfileRunRequest`/`ProfileRunResult` contract. Geometry is explicit and
fail-closed: memory size equals the ternary word modulus, EOF equals modulus minus
one, and the modulus must equal `3^word_trits`. Scalable memory is represented as
contiguous 32-bit words rather than boxed Python integers. The shared resident
kernel specializes crazy width, rotate high-trit weight, EOF, wrap modulus, and
memory geometry at NVRTC compile time while retaining the same instruction tables
and atomic transition rules.

`tests/vm/cuda_profile_run.rs` obtains geometry exclusively from canonical Rust
`current_profile()` and compares eight complete `malbolge-2026.2` cases against
`ProfileMachine`. The RTX 4060 / `sm_89` differential compares every one of the
4,782,969 final memory words plus registers, input/output, termination, step
counts, and rejection details. Cases cover the real six-step current program with
input and EOF, rejected jump atomicity, non-graphical termination, maximum-pointer
wrap, bounded budget exhaustion, live checkpoint resumption, and
already-terminated execution. CUDA remains optional and is not profile
authority. Rust product-batch integration additionally exercises the real classic
and current workers through hardware-neutral backend traits; unavailable,
deferred, or structurally invalid attempts fall back to untouched safe-Rust
states. The retained RTX 4060 baseline measures 15 samples per complete-snapshot
batch point and originally reached about 40.08 VMs/s at batch 32. Device-side
replication now copies one shared initial image from host and expands it into
private per-VM regions in VRAM; post-change batch 32 reaches about 51.67 VMs/s
with median upload time about 6.93x lower. Persistent profile sessions keep those
private states resident across bounded launches and reach about 2.00 million
64-step VM segments/s at batch 128 when setup, observation, and snapshots are
outside the timed region. Validated `ProfileMemoryImage` inputs additionally
reuse their geometry/domain proof across calls: retained batch-32 validation and
planning falls to about 0.23 ms and complete-snapshot throughput reaches about
93.68 VMs/s. Resident sessions now expose diagnostic `profile_snapshot()` without
changing ordinary snapshot semantics. It separates fresh host-array allocation,
state/memory/output D-to-H, decode, and total. Retained RTX 4060 batches 1/8/32
measure 3.1616/65.7829/271.1391 ms. Batch 1 is 96.489% transfer; batches 8/32
are 62.419%/63.872% allocation and 37.248%/35.962% memory transfer. Ordinary resident snapshots now always return fresh independent mutable arrays.
The separately admitted `caller-owned-independent-u32-arrays-v1` workspace makes
reuse and overwrite semantics explicit, validates shape/proof/session identity, and
reports allocation outside the repeated path. Retained batches 1/8/32 improve
2.586x/2.667x/2.712x with median-derived crossover 1/2/2; batch-one margin is
narrow and batches 8/32 recover allocation on the second snapshot. The stable arrays
select bounded host registration/page-locking as the next CUDA experiment.
These are backend
measurements, not CPU-relative or cross-device speedup claims.

## Invariants

- CUDA kernels implement exact discrete VM semantics for independent batches and
  are differentially checked against the CPU reference across randomized and
  boundary-heavy corpora.
- A CPU/reference path remains sufficient for correctness, and accelerator
  failure/unavailability changes performance rather than semantic acceptance.

## Failure Behavior

Missing hardware, resource exhaustion, or accelerator disagreement falls back or
fails explicitly without changing correctness rules.

## Verification

- Expected durable artifact surface: `accelerator/`, `algorithms/`,
  `optimizer/`, `benchmarks/accelerator/`, `tests/optimizer/`.
- `tests/optimizer/test_exact_accelerator_primitives.py` executes the reviewed
  CUDA kernels when a device is available and compares every result to the CPU
  adapter. Missing CUDA is reported as unavailable/skip; actual execution
  disagreement is a test failure.
- The current workstation evidence is RTX 4060 / `sm_89`; toolchain smoke also
  verifies NVRTC -> PTX -> Driver API execution with the pinned CUDA 13.3 Update
  1 redistributables.
- Compact classic-step differential evidence covers VM state/I/O/mutation trace
  projections and atomic rejection. Resident classic evidence compares complete
  59,049-word states; scalable resident evidence compares complete 4,782,969-word
  current-profile states against normative Rust. Product-level batch routing, an
  RTX 4060 current-profile baseline, device-side shared initialization,
  validated-memory, direct-snapshot, and persistent-session evidence are retained.
  The hardware-neutral exact-primitive candidate bridge also executes 257-item
  classic crazy and rotate corpora on live CUDA and matches CPU evidence exactly.
  Verification-assist now reuses exact candidate evidence through the same live
  CUDA backend over a deterministic 257-item rotate corpus; those results remain
  untrusted hints and malformed optional evidence becomes no hint. The bounded
  `classic-rotate-target-search-v1` strategy now uses live CUDA candidate
  evaluation through the neutral search port over 257 deterministic candidates,
  records CUDA as the actual backend, matches CPU proposals, and leaves acceptance
  to an independent CPU verifier. A separate protocol-compliant full-domain run
  retains 15 CPU and 15 CUDA samples over 59,049 candidates. CPU median is
  401.185 ms and CUDA median is 412.570 ms on the RTX 4060, yielding 0.972x
  CUDA/CPU and rejecting the speedup hypothesis for this complete host-heavy
  route. Exact proposal equality and CPU admission still pass for every sample.
  The companion phase profile attributes 99.5% of CUDA median total time to named
  phases: about 57.0% host-side and 42.5% backend evaluation. Batch construction
  plus proposal selection consume about 173.081 ms. Hardware-neutral prepared
  search state is now active: CPU-prepared immutable request/batch state executes
  unchanged through the matching CUDA strategy, while forged or mismatched proof
  identity fails closed. Prepared execution removes repeated batch build/validation
  from the timed repeated-search path, and rotate-target selection avoids a second
  full corpus decode. The retained four-route comparison records CUDA ordinary
  and prepared medians of 306.872 and 162.693 ms (1.886x). CPU prepared reaches
  148.590 ms, leaving prepared CUDA about 9.5% slower (0.913x
  CPU-prepared/CUDA-prepared). Preparation is outside timed intervals, so this is
  repeated-search evidence rather than one-shot latency. The retained prepared
  phase profile attributes 138.320 ms, or 81.2% of CUDA median total time, to
  backend evaluation and 31.912 ms, or 18.7%, to proposal selection. Proof/result
  validation is negligible. Primitive CUDA evidence now returns one fixed-width
  packed byte buffer instead of 59,049 logical-ID/bytes objects. Batch order carries
  identity, malformed packed shape fails closed, and rotate search consumes packed
  u32 values directly. Verification-assist materializes only when explicit hints
  are requested. Retained packed evidence lowers CUDA ordinary/prepared medians
  from 306.872/162.693 to 230.144/91.199 ms (1.333x/1.784x). Backend evaluation
  falls from 138.320 to 67.202 ms (2.058x), and selection from 31.912 to
  22.288 ms (1.432x). Packed CUDA prepared remains about 18.0% slower than packed
  CPU prepared. Rotate prepared state now includes one validated decoded
  `PrimitiveBatch` produced independently of CUDA identity. Matching CUDA execution
  consumes that state without repeating candidate ID validation or payload decode;
  forged type/kind/evaluator state fails before device work. Retained CUDA prepared
  median falls from 91.199 to 57.296 ms (1.592x), and backend evaluation falls from
  67.202 to 32.264 ms (2.083x). Ordinary CUDA regresses 3.7%; prepared CUDA remains
  32.8% slower than prepared CPU. Prepared exact primitives now retain one
  proof-bound device input/output allocation and host output buffer. The same proof
  reuses that session; a different proof releases/rebuilds it, and close releases it
  before module/context teardown. Ordinary evaluation keeps per-call allocation and
  transfer. Benchmarks require explicit one-build/15-reuse counters. Retained CUDA
  prepared median is 34.132 ms, 1.679x faster than the 57.296 ms pre-resident
  baseline and 1.355x faster than same-run CPU prepared. CUDA backend evaluation
  falls from 32.264 to 9.922 ms (3.252x). Complete CUDA phase total changes from
  55.300 to 55.910 ms because selection rises to 46.331 ms; no total phase speedup
  is claimed. The shared prepared-search proof now also carries an immutable exact
  59,049-member proposal index. CUDA and CPU prepared routes reuse it after evidence
  selection; ordinary routes retain one-shot membership construction, and forged
  payloads fail closed. Retained CUDA prepared median reaches 17.970 ms, 1.899x
  faster than the resident baseline and 1.491x faster than same-run CPU. CUDA
  proposal selection falls from 46.331 to 11.761 ms (3.939x). Improved ordinary and
  backend controls bound cross-run attribution. The neutral prepared proof now
  also contains exact rotate-preimage positions after pruning/seed/budget. CUDA
  prepared selection reads and validates only those packed words; ordinary CUDA
  search retains the full host scan. Benchmarks require one selector position
  alongside membership and resident-session identity. Retained CUDA prepared median
  is 6.182 ms, 2.907x faster than indexed membership and 2.470x faster than same-run
  CPU. CUDA selection falls from 11.761 ms to 12.4 us (948.452x), while backend
  evaluation changes only 1.035x to 5.239 ms. Primitive result validation now uses
  exact tuple extrema and continues rejecting negative or above-domain output before
  packing. Retained CUDA prepared median falls from 6.182 to 4.929 ms (1.254x), and
  backend evaluation from 5.239 to 3.940 ms (1.330x). CUDA ordinary remains nearly
  flat/slightly slower. Prepared CPU rotate now has an exact scalar-derived lookup
  table with explicit benchmark counters. Retained CPU/CUDA prepared medians are
  3.313/4.769 ms, so CPU prepared is 1.440x faster in the same run. CUDA backend
  evaluation changes only 1.018x to 3.868 ms, so no CUDA-table speedup is claimed.
  Prepared CUDA now returns canonical packed u32le output directly from the resident
  host buffer after D-to-H transfer. This removes tuple materialization and array
  repacking, but the neutral candidate bridge still validates capability, exact
  byte count, and every output word before acceptance. Ordinary CUDA remains
  tuple-based. `packed_evaluations` makes route use observable, and benchmarks
  require 16 packed evaluations. Retained CUDA prepared median falls from 4.769
  to 2.036 ms (2.343x), and backend evaluation from 3.868 to 1.802 ms (2.147x).
  Same-run CUDA prepared is 1.621x faster than CPU; CPU phases change only about
  0.5%. Packed-domain validation now uses `u32le-broadword-domain-v1`. Repeated
  high-bit masks and lane-independent threshold addition validate all words through
  big-integer operations; scalar decoding runs only after failure to report the
  invalid maximum. First/last-lane threshold and high-bit adversaries fail closed,
  and benchmarks require the identity. Retained CUDA prepared median falls from
  2.036 to 1.175 ms (1.733x), backend evaluation from 1.802 to 0.860 ms (2.095x),
  and total from 1.824 to 0.886 ms (2.057x). CUDA is 2.706x faster than same-run CPU.
  CPU phase regressions remain controls. `CudaPreparedPrimitivePhaseProfile`
  exposes launch/synchronization, D-to-H transfer, immutable-byte copy, and total
  diagnostics from the exact resident route. The neutral packed profile separately
  exposes contract, mask lookup, integer decode, high-mask, threshold, diagnostic,
  result construction, and total. The dedicated full-domain benchmark requires
  byte-identical CPU evidence, validator identity, 1/16/16/15 session counters, and
  visible phase accounting. Prepared candidate state now computes immutable CPU
  truth once and validates CUDA bytes under `cpu-reference-packed-equality-v1`;
  ordinary CUDA retains `u32le-broadword-domain-v1`. Capability, immutable bytes,
  exact count, and equality precede evidence acceptance. First/final in-domain drift
  fails closed. The profiler records exact compare instead of broadword decode/checks
  and exposes residual layer overhead; search benchmarks prove 59,049 reference
  words plus all existing counters. Retained CUDA prepared search reaches 0.488 ms
  (2.407x better), CUDA backend/total reach 0.215/0.238 ms (3.999x/3.729x), and exact
  prepared validation reaches 0.0278 ms (23.590x) with 0.0180 ms comparison.
  Primitive end-to-end reaches 0.1935 ms (4.488x). The reference image is 236,196
  bytes and construction remains outside timed execution. The active four-scale
  benchmark measures cold/warm preparation, incremental Python memory, fresh
  resident build, steady reuse, and strict crossover while requiring validator,
  proposal/admission, state-count, and session proofs. Retained warm/cold crossover
  is 6/3/2/1 and 106/38/5/2. Full-domain warm preparation plus first search is
  212.140 ms versus 222.842 ms ordinary; cold crosses on run two. Incremental Python
  state retains/peaks at 16.063/19.040 MiB versus 0.901 MiB exact buffers.   Component tracing selected the historical prepared membership frozenset for the
  first compaction. The replacement retains sorted references to the original batch,
  is proof-bound to that batch, and checks binary-searched logical IDs with exact
  payload equality. Forged/cross-batch indexes and proposal substitution fail
  closed. Retained version-2 evidence under
  `benchmarks/accelerator/evidence/2026-07-28-compact-membership-crossover-rtx4060/`
  records 473,352 bytes compact component retention versus 5,876,552 bytes copied
  (91.945% lower), 15.851/18.027 ms preparation (1.137x compact advantage), and
  32.083%/26.051% lower complete prepared retention/peak. Exact compact hit/miss
  lookup is 9.898x/13.856x slower, so promotion is for memory/preparation rather than
  lookup speed. Warm/cold crossover is 7/3/2/1 and 108/38/5/1. This is the retained
  version-2 baseline.
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
  moves from 6/6 to 8/7. The next architectural boundary is an exact projected-subset
  contract for strategies without a unique algebraic inverse; any generalization must
  retain subset identity, full membership, exact evidence, proposal validation, and
  independent trusted admission rather than introduce heuristic filtering.
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
optimization. The next production boundary is the first real non-invertible or
multi-position strategy that can supply exact positions without heuristic filtering.
  Broader live-hardware evidence, synthesis/search
  strategies, resident search designs, and ROCm work remain before this TODO can
  complete.
- Prerequisite completion evidence: `replaceable-accelerator-boundary`,
  `batch-vm-execution`.
## References

### Host Architecture Baseline

- `docs/technical/adr/host-cpu-and-accelerator-runtime-baseline.md`

- [Replaceable Accelerator And Algorithm
  Ports](../../adr/replaceable-accelerator-and-algorithm-ports.md)
- [Verification Trust Boundary](../../adr/verification-trust-boundary.md)

### Governing ADR Paths

- `docs/technical/adr/replaceable-accelerator-and-algorithm-ports.md`
- `docs/technical/adr/verification-trust-boundary.md`
