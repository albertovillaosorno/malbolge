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
sessions; none changes semantic authority or establishes a CPU-relative speedup.
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
cross-batch proofs, and payload substitution still fail closed. The retained
prepared primitive Python integer tuple is the next measured memory boundary.
Resident/fused search remains later work.
Synthesis/guided search
algorithms, asynchronous submission, and ROCm remain open.

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
- `tests/optimizer/test_accelerator_work_ports.py` verifies CPU fallback,
  malformed optional-result fallback, stable algorithm/seed/budget identity,
  optional verification hints, and verifier-only candidate admission.
- Remaining evidence includes concrete algorithm adapters, CUDA/ROCm work-port
  implementations, ROCm VM substitution, asynchronous submission, broader
  hardware evidence, and matched measurements for future speedup claims.
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
