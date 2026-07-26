# ROCm accelerator adapter

## Status

Proposed

## Purpose

Add a ROCm accelerator implementation behind the same hardware-neutral port
without changing compiler semantics, target profiles, or verifier contracts.

## Scope

This document governs the following declared TODO scope:

- `accelerator/rocm/`
- `algorithms/`
- `optimizer/`
- `benchmarks/accelerator/`
- `tests/optimizer/`

## Current Behavior

### Proposed Model

This record defines the contract that implementation must satisfy for
`rocm-accelerator-adapter`. The implementation may change internal
representation or language choices without changing the observable behavior,
trust boundary, or ownership rules stated by its governing decisions.

### Implementation Status

Not implemented. This proposed contract does not claim executable support yet.

## Invariants

- The ROCm adapter satisfies the same capability/algorithm contracts without
  CUDA types, APIs, or configuration becoming required by shared compiler code.
- ROCm/HIP/runtime identity is recorded in experiment and benchmark evidence
  when the adapter participates in a result.
- A CPU/reference path remains sufficient for correctness, and accelerator
  failure/unavailability changes performance rather than semantic acceptance.

## Failure Behavior

Missing hardware, resource exhaustion, or accelerator disagreement falls back or
fails explicitly without changing correctness rules.

## Verification

- Expected durable artifact surface: `accelerator/rocm/`, `algorithms/`,
  `optimizer/`, `benchmarks/accelerator/`, `tests/optimizer/`.
- Required evidence: CPU/reference differential results against x86-64 and
  AArch64 hosts, ROCm device/runtime metadata, failure/fallback tests, and
  benchmark samples for claimed speedups.
- Prerequisite completion evidence: `replaceable-accelerator-boundary`,
  `configurable-accelerator-algorithm-adapters`.
## References

### Host Architecture Baseline

- `docs/technical/adr/host-cpu-and-accelerator-runtime-baseline.md`

- [Replaceable Accelerator And Algorithm
  Ports](../../adr/replaceable-accelerator-and-algorithm-ports.md)
- [Verification Trust Boundary](../../adr/verification-trust-boundary.md)

### Governing ADR Paths

- `docs/technical/adr/replaceable-accelerator-and-algorithm-ports.md`
- `docs/technical/adr/verification-trust-boundary.md`
