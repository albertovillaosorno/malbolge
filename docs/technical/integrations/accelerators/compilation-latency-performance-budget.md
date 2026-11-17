# Compilation latency performance budget

## Status

Proposed

## Purpose

Define measurable latency budgets for the compiler without confusing raw
synthesis complexity with compositional reuse, accelerator throughput, or a warm
resident cache. The budget exists to make interactive compilation an evidence-
backed engineering objective rather than an unsupported promise.

## Scope

This document governs the following declared TODO scope:

- `accelerator/`
- `algorithms/`
- `optimizer/`
- `compiler/server/`
- `benchmarks/accelerator/`
- `benchmarks/compiler/`
- `tests/optimizer/`

## Current Behavior

### Proposed Model

Latency reports classify each build by workload/difficulty, target profile,
algorithm, hardware, cache/catalogue generation, and cold/warm state. Timings
are
split into frontend work, lowering, invalidation, search, catalogue lookup,
verification, link/stitch, serialization/IPC, and artifact emission.

Interactive targets such as "seconds, not hours" are performance goals. They do
not imply a particular asymptotic law and may be satisfied by verified reuse
even
when the underlying uncached search remains expensive.

### Implementation Status

Not implemented. No latency target or scaling law is currently claimed.

## Bounded Acceptance (2026-11-16)

- Establish the first cold CPU reference budget before resident compilation,
  CUDA and the empirical scaling law are complete. Report only implemented
  timing stages; absent IPC, cache, invalidation or accelerator lanes are N/A,
  not zero, not a hidden prerequisite, and never omitted from method notes.

## Invariants

- Cold, warm, incremental, and novel-search measurements are labeled separately.
- A cache hit or reusable block does not retroactively redefine raw search cost.
- CPU/reference paths remain semantically authoritative enough for correctness.
- Accelerator, cache, or resident-server failures never weaken verifier rules.
- Reported scaling conclusions cite the exact empirical regime and retained raw
  evidence.

## Failure Behavior

Missing hardware, resource exhaustion, stale cache state, failed recovery, or
accelerator disagreement falls back or fails explicitly without changing
correctness rules. A missed latency target is recorded as evidence, not hidden
by
changing the workload or excluding failed searches.

## Verification

- Baseline benchmarks retain raw CPU cold samples with exact software and
  hardware identity; warm/incremental samples are added once those modes exist.
- Resident and cold builds are compared if resident compilation exists;
  they cannot block the initial CPU compile-time budget.
- Failure/fallback runs prove accelerator and server unavailability affect only
  performance.
- Scaling claims cite empirical measurements if available; a budget alone
  does not assert any asymptotic complexity class.

## References

- [Replaceable Accelerator And Algorithm
  Ports](../../adr/replaceable-accelerator-and-algorithm-ports.md)
- [Verification Trust Boundary](../../adr/verification-trust-boundary.md)
- [Resident incremental compiler and
  WAL](../../compiler/resident-incremental-compiler-and-wal.md)
- [Empirical Malbolge synthesis scaling
  law](../../../research/studies/empirical-malbolge-synthesis-scaling-law.md)

### Governing ADR Paths

- `docs/technical/adr/replaceable-accelerator-and-algorithm-ports.md`
- `docs/technical/adr/verification-trust-boundary.md`
