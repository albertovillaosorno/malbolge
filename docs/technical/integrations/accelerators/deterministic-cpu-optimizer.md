# Deterministic CPU optimizer

## Status

Active implementation

## Purpose

Implement a correct CPU reference optimizer and search engine that remains
available without a GPU and serves as the specification-conformant baseline on
both x86-64 and AArch64 hosts.

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
`deterministic-corpus-enumeration-v1` under `optimizer/enumerative.py`. Its
problem is an explicitly supplied finite corpus with canonical binary encoding.
The request seed selects a deterministic starting ordinal and the evaluation
budget bounds how many distinct candidates are proposed without wraparound
duplication. Stable logical candidate IDs preserve replay identity.

The strategy runs through `CpuSearchExecutionAdapter` and the shared search port.
It produces only untrusted `CandidateProposal` values; `search_and_verify()`
passes those proposals to an independent `TrustedCandidateVerifier`, which alone
decides acceptance. GPU availability is irrelevant to this path.

### Implementation Status

A bounded deterministic CPU baseline is active and plugs into the generic
algorithm/backend registry. It proves reproducible CPU-only search, canonical
problem replay, explicit seed/budget control, and independent verification. It is
not a claim that general Malbolge synthesis is solved. Real synthesis generators,
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
  roundtrip, seeded order, budget bounds, duplicate rejection, malformed
  encodings, trusted-verifier admission, and generic search-registry integration.
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
