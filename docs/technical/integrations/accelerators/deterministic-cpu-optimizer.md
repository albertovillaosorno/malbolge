# Deterministic CPU optimizer

## Status

Active implementation

## Purpose

Implement a correct CPU reference optimizer and search engine that remains
available without a GPU and serves as the declared-profile-conformant baseline
on both x86-64 and AArch64 hosts.

## Scope

This document governs the following declared TODO scope:

- `accelerator/cpu/`
- `algorithms/`
- `optimizer/`
- `benchmarks/accelerator/`
- `tests/optimizer/`

## Current Behavior

### Active Model

The first concrete CPU search strategy is
`deterministic-corpus-enumeration-v1` under
`src/optimization/optimizer/application/optimizer/enumerative.py`. Its
problem is an explicitly supplied finite corpus with canonical binary encoding.
Direct problem objects require immutable tuple/bytes storage, while classic
rotate/crazy target parameters and candidates require exact integers. Mutable
containers, boolean or floating-point words, and mutable encoded payloads fail
before search. The encoded problem preserves the complete supplied corpus,
including exact duplicates, for replay identity. Before assigning logical
candidate IDs,
`src/optimization/optimizer/application/optimizer/pruning.py` partitions
payloads only by complete byte equality and
retains each first occurrence. The request seed rotates over those exact
representatives, and evaluation budget counts distinct retained candidates
rather
than duplicate input positions. Stable logical IDs retain the first original
corpus index.

The strategy runs through `CpuSearchExecutionAdapter` and the shared search
port.
It produces only untrusted `CandidateProposal` values; `search_and_verify()`
passes those proposals to an independent `TrustedCandidateVerifier`, which alone
decides acceptance. GPU availability is irrelevant to this path.

A second bounded reference, `classic-rotate-target-search-v1`, searches an
explicit classic-word corpus for inputs whose exact rotate result equals one
target. It uses the same `EvaluatedSearchExecutionAdapter` strategy shape as the
optional CUDA route, but binds the exact CPU primitive evaluator. Exact
duplicate
inputs are pruned by stable first representative, seed rotates the
representative
order, budget bounds candidate evaluations, and `RotateTargetVerifier`
recomputes
acceptance independently on CPU. The external `python -m optimizer.cli` runner
can select either CPU reference through Search Configuration v1 and records
canonical problem hash plus configured/actual execution identity without
claiming
proposal acceptance.

### Implementation Status

A bounded deterministic CPU baseline is active and plugs into the generic
algorithm/backend registry. It proves reproducible CPU-only search, canonical
problem replay, explicit seed/budget control, and independent verification. It
is
not a claim that general Malbolge synthesis is solved. Real synthesis
generators,
translation-validation integration, AArch64 execution evidence, and performance
benchmarks remain open.

## Invariants

- The CPU-only optimizer/search path produces and verifies candidates without
  GPU availability on both x86-64 and AArch64.
- Architecture-specific performance tuning may differ, but candidate semantics,
  verifier obligations, and experiment identity remain shared.
- A CPU/reference path remains sufficient for correctness, and accelerator
  failure/unavailability changes performance rather than semantic acceptance.

## Failure Behavior

Missing hardware, resource exhaustion, or accelerator disagreement falls back or
fails explicitly without changing correctness rules.

## Verification

- Expected durable artifact surface: `accelerator/cpu/`, `algorithms/`,
  `optimizer/`, `benchmarks/accelerator/`, `tests/optimizer/`.
- Required evidence: CPU/reference differential results, device/resource
  metadata, failure/fallback tests, and benchmark samples for claimed speedups.
- `tests/optimizer/test_deterministic_enumeration.py` covers canonical problem
  roundtrip, seeded representative order, budget bounds, duplicate-preserving
  input replay with exact pre-identity pruning, malformed encodings,
  trusted-verifier admission, and generic search-registry integration.
- `tests/optimizer/test_exact_duplicate_pruning.py` matches the production
  Python
  relation against the retained duplicate-rich/null/adversarial research
  fixtures;
  the independent Rust mirror keeps the same five adversarial checks.
- `tests/optimizer/test_rotate_target_search.py` verifies canonical problem
  replay,
  duplicate pruning, seed/budget bounds, CPU search, live CUDA differential
  search,
  actual-backend identity, independent CPU admission, and malformed-backend CPU
  fallback. This is a bounded exact-search fixture, not general synthesis.
- `tests/optimizer/test_crazy_target_search.py` verifies the first exact
  non-invertible multiposition strategy: shared ternary semantics,
  fixed-accumulator
  full-domain membership, exact 1,024-position projection, CPU/CUDA prepared
  equality, and independent admission. Its sibling ticket tests retain nested
  lifetime, malformed-protocol, exact CUDA publication, and teardown fallback.
- `benchmarks/accelerator/evidence/2026-07-27-rotate-target-search-rtx4060/`
  retains the complete 59,049-word CPU/CUDA comparison. The CPU reference median
  is 401.185 ms versus 412.570 ms for CUDA, so this CPU baseline wins by median
  and the 0.972x CUDA/CPU result is retained as negative evidence.
<!-- jig-ignore-next-line: canonical path or identifier is indivisible -->
- `benchmarks/accelerator/evidence/2026-07-29-crazy-target-performance-matrix-rtx4060/`
  retains the multiposition crazy-target matrix. CPU ordinary/prepared
  medians are 368.3588/22.4264 ms (16.425x, 15/15 paired wins); CUDA
  ordinary/prepared medians are 235.8490/20.3304 ms (11.601x, 15/15 wins). The
  one-shot CUDA ticket reaches 185.7629 ms (1.270x over ordinary, 15/15 wins)
  but
  remains 9.137x slower than amortized prepared CUDA. Every route preserves the
  same 1,024 proposals and independent CPU admission.
<!-- jig-ignore-next-line: canonical path or identifier is indivisible -->
- `benchmarks/accelerator/evidence/2026-07-27-rotate-target-search-phase-profile-rtx4060/`
  retains diagnostic attribution. Named phases explain 97.5% of CPU median total
  time and identify batch construction (132.653 ms), backend evaluation
  (132.738 ms), and proposal selection (52.029 ms) as the dominant CPU phases.
- Prepared evaluated-search state now validates and builds this exact CPU batch
  once, supports repeated execution and post-preparation phase diagnostics, and
  can be consumed unchanged by the matching CUDA strategy. Rotate-target
  selection
  decodes only the validated target/header. Retained repeated-search evidence
  records
  a CPU ordinary median of 293.564 ms and prepared median of 148.590 ms
  (1.976x).
  Preparation is outside timed intervals, and every sample preserves independent
  admission. The prepared phase profile places 125.412 ms, or 79.9% of CPU
  median
  total time, in backend evaluation and 30.796 ms, or 19.6%, in proposal
  selection.
  The CPU primitive bridge now emits fixed-width packed evidence, so search
  reads
  u32 results without constructing per-candidate evidence bytes/objects. Generic
  item results and explicit hint materialization remain supported. Retained
  packed
  evidence lowers CPU ordinary/prepared medians from 293.564/148.590 to
  211.693/77.309 ms (1.387x/1.922x). Backend evaluation falls from 125.412 to
  53.907 ms (2.326x) and selection from 30.796 to 22.502 ms (1.369x). Rotate
  preparation now validates/decodes the exact candidate batch once and stores a
  hardware-neutral `PrimitiveBatch` in the strategy proof. Repeated CPU
  execution
  no longer pays candidate batch validation or payload decode. Retained CPU
  prepared
  median falls from 77.309 to 43.129 ms (1.792x), and backend evaluation from
  53.907 to 19.246 ms (2.801x). Ordinary CPU regresses 6.6% because it
  constructs
  the proof locally. `PreparedPrimitiveBatch` now seals validation once and the
  CPU
  prepared port consumes it without a second scan. In the resident-session run
  CPU
  prepared records 46.232 ms, 7.2% slower than the prior run amid broader
  control
  regressions; no CPU improvement is claimed. Prepared state now stores an
  immutable
  exact candidate membership index, so repeated CPU proposal validation no
  longer
  rebuilds the 59,049-entry dictionary. Ordinary execution is unchanged and
  forged
  payloads still fail closed. Retained CPU prepared median reaches 26.797 ms,
  1.725x faster than the resident baseline, while selection falls from 41.529 to
  11.801 ms (3.519x). Improved ordinary/backend controls bound total
  attribution.
  Prepared rotate selection now computes the unique inverse candidate and stores
  only positions that survive pruning/seed/budget. It reads/verifies evidence at
  those positions instead of scanning every packed word; ordinary CPU search
  keeps
  the scan. Missing/excluded candidates and nonmatching evidence produce no
  proposal. Retained CPU prepared median reaches 15.266 ms, 1.755x faster than
  indexed membership, while selection falls from 11.801 ms to 13.2 us
  (894.008x).
  Backend evaluation remains 14.387 ms and changes only 1.034x. Primitive result
  validation now uses exact tuple extrema instead of a Python per-value loop and
  still rejects negative or above-domain output. Retained CPU prepared median
  falls
  from 15.266 to 14.058 ms (1.086x), and backend evaluation from 14.387 to
  13.190 ms (1.091x). Prepared rotate now uses a cached 59,049-entry lookup
  table
  generated once from the scalar formula; ordinary CPU remains scalar. The
  exhaustive differential test compares every classic-domain input, and
  benchmark
  diagnostics require 16 prepared evaluations plus full table cardinality.
  Retained
  CPU prepared median falls from 14.058 to 3.313 ms (4.243x), while backend
  evaluation falls from 13.190 to 2.906 ms (4.540x). CPU ordinary is effectively
  unchanged and CPU prepared is 1.440x faster than same-run CUDA. Result
  validation/packing is the next CPU target.
- Prerequisite completion evidence: `safe-rust-malbolge-vm`,
  `translation-validation`, `compiler-algorithm-experimentation-platform`.
## References

### Host Architecture Baseline

- `docs/technical/adr/host-cpu-and-accelerator-runtime-baseline.md`

- [Replaceable Accelerator And Algorithm
  Ports](../../adr/replaceable-accelerator-and-algorithm-ports.md)
- [Verification Trust Boundary](../../adr/verification-trust-boundary.md)

### Governing ADR Paths

- `docs/technical/adr/replaceable-accelerator-and-algorithm-ports.md`
- `docs/technical/adr/verification-trust-boundary.md`
