# Reusable block catalogue

- Status: Proposed
- Planning identity: `reusable-block-catalogue`
- Last reviewed: 2026-07-26

## Governing Decisions

- [Replaceable Accelerator And Algorithm
  Ports](../adr/replaceable-accelerator-and-algorithm-ports.md)
- [Verification Trust Boundary](../adr/verification-trust-boundary.md)

## Purpose

Build a deterministic catalogue of verified arithmetic, branch, memory, calling
convention, and runtime blocks so common operations are solved once and reused
instead of synthesized from scratch for every compilation.

## Proposed Model

This record defines the contract that implementation must satisfy for
`reusable-block-catalogue`. The implementation may change internal
representation or language choices without changing the observable behavior,
trust boundary, or ownership rules stated by its governing decisions.

## Invariants

- Every catalog entry binds semantic pre/postconditions, profile constraints,
  cost metrics, provenance, and verifier identity; lookup never substitutes a
  block whose contract does not match.
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
