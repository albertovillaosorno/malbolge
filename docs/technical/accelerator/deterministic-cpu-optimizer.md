# Deterministic CPU optimizer

- Status: Proposed
- Planning identity: `deterministic-cpu-optimizer`
- Last reviewed: 2026-07-26

## Governing Decisions

- [Replaceable Accelerator And Algorithm
  Ports](../adr/replaceable-accelerator-and-algorithm-ports.md)
- [Verification Trust Boundary](../adr/verification-trust-boundary.md)

## Purpose

Implement a correct CPU reference optimizer and search engine that works without
a GPU, even when much slower, and acts as the semantic baseline for accelerator
implementations.

## Proposed Model

This record defines the contract that implementation must satisfy for
`deterministic-cpu-optimizer`. The implementation may change internal
representation or language choices without changing the observable behavior,
trust boundary, or ownership rules stated by its governing decisions.

## Invariants

- A CPU-only optimizer/search path can produce and verify candidates without GPU
  availability and serves as the reproducible semantic baseline for accelerator
  strategies.
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
