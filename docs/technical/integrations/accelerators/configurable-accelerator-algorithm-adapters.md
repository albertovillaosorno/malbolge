# Configurable accelerator algorithm adapters

## Status

Active implementation

## Purpose

Separate optimization/search strategy from accelerator hardware. Define common
algorithm ports for enumerative, stochastic, Monte Carlo, evolutionary, learned,
hybrid, pruning, and future strategies, and let CPU, CUDA, ROCm, or later
hardware adapters provide execution capacity for those strategies. Select
algorithms and hardware through deterministic configuration with optional CLI
overrides, record the exact combination in benchmark evidence, and permit side-
by-side comparison without recompiling or modifying compiler semantics.

## Scope

This document governs the following declared TODO scope:

- `accelerator/`
- `algorithms/`
- `optimizer/`
- `benchmarks/accelerator/`
- `tests/optimizer/`

## Current Behavior

### Active Model

`SearchRequest` binds an algorithm ID, deterministic seed, evaluation budget, and
opaque problem bytes independently from backend capability.
`SearchExecutionAdapter` supplies execution capacity only; returned
`CandidateProposal` values are untrusted until `TrustedCandidateVerifier` admits
them. `CpuSearchExecutionAdapter` supplies the mandatory portable callback path.
The same boundary separates candidate-evaluation evidence and optional
verification hints from candidate acceptance.

### Implementation Status

The selection-independent contract is active. Algorithm ID is request identity
while `AcceleratorCapability` is backend identity, so the two dimensions are
recorded independently. `SearchSelection` plus `SearchAdapterBinding` resolve one
mandatory `cpu-reference` implementation and an optional preferred backend.
Algorithm/backend overrides are explicit and unsupported combinations fail
before search starts. `SearchRunIdentity` records both configured and actual
backend IDs, so a CPU fallback cannot be mislabeled as accelerated evidence.
The first concrete strategy is `deterministic-corpus-enumeration-v1`, bound to
the mandatory CPU reference through the same registry. Additional research
strategies, CLI front-end wiring, accelerator implementations, and comparative
benchmark evidence remain open.

## Invariants

- Hardware backend and search/optimization strategy are independently selected;
  unsupported combinations fail explicitly and benchmark identity records both
  dimensions.
- A CPU/reference path remains sufficient for correctness, and accelerator
  failure/unavailability changes performance rather than semantic acceptance.

## Failure Behavior

Missing hardware, resource exhaustion, or accelerator disagreement falls back or
fails explicitly without changing correctness rules.

## Verification

- Expected durable artifact surface: `accelerator/`, `algorithms/`,
  `optimizer/`, `benchmarks/accelerator/`, `tests/optimizer/`.
- Required evidence: CPU/reference differential results, device/resource
  metadata, failure/fallback tests, and benchmark samples for claimed speedups.
- Prerequisite completion evidence: `replaceable-accelerator-boundary`,
  `algorithm-research-mirror-and-local-output-contract`.
## References

### Host Architecture Baseline

- `docs/technical/adr/host-cpu-and-accelerator-runtime-baseline.md`

- [Replaceable Accelerator And Algorithm
  Ports](../../adr/replaceable-accelerator-and-algorithm-ports.md)
- [Verification Trust Boundary](../../adr/verification-trust-boundary.md)

### Governing ADR Paths

- `docs/technical/adr/replaceable-accelerator-and-algorithm-ports.md`
- `docs/technical/adr/verification-trust-boundary.md`
