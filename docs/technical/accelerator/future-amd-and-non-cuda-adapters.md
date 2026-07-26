# Future AMD and non-CUDA adapters

- Status: Proposed
- Planning identity: `future-amd-and-non-cuda-adapters`
- Last reviewed: 2026-07-26

## Governing Decisions

- [Replaceable Accelerator And Algorithm
  Ports](../adr/replaceable-accelerator-and-algorithm-ports.md)
- [Verification Trust Boundary](../adr/verification-trust-boundary.md)

## Purpose

Add interchangeable AMD and other accelerator implementations without changing
compiler semantics, target profiles, or verifier contracts.

## Proposed Model

This record defines the contract that implementation must satisfy for
`future-amd-and-non-cuda-adapters`. The implementation may change internal
representation or language choices without changing the observable behavior,
trust boundary, or ownership rules stated by its governing decisions.

## Invariants

- At least one non-CUDA adapter can satisfy the same capability/algorithm
  contracts without CUDA types, APIs, or configuration becoming required by
  shared compiler code.
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
