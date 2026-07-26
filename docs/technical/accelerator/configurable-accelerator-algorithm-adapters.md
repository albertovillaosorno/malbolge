# Configurable accelerator algorithm adapters

- Status: Proposed
- Planning identity: `configurable-accelerator-algorithm-adapters`
- Last reviewed: 2026-07-26

## Governing Decisions

- [Replaceable Accelerator And Algorithm
  Ports](../adr/replaceable-accelerator-and-algorithm-ports.md)
- [Verification Trust Boundary](../adr/verification-trust-boundary.md)

## Purpose

Separate optimization/search strategy from accelerator hardware. Define common
algorithm ports for enumerative, stochastic, Monte Carlo, evolutionary, learned,
hybrid, pruning, and future strategies, and let CPU, CUDA, AMD, or later
hardware adapters provide execution capacity for those strategies. Select
algorithms and hardware through deterministic configuration with optional CLI
overrides, record the exact combination in benchmark evidence, and permit side-
by-side comparison without recompiling or modifying compiler semantics.

## Proposed Model

This record defines the contract that implementation must satisfy for
`configurable-accelerator-algorithm-adapters`. The implementation may change
internal representation or language choices without changing the observable
behavior, trust boundary, or ownership rules stated by its governing decisions.

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

## Implementation Status

Not implemented. This proposed contract does not claim executable support yet.
