# Replaceable accelerator boundary

- Status: Proposed
- Planning identity: `replaceable-accelerator-boundary`
- Last reviewed: 2026-07-26

## Governing Decisions

- [Replaceable Accelerator And Algorithm
  Ports](../adr/replaceable-accelerator-and-algorithm-ports.md)
- [Verification Trust Boundary](../adr/verification-trust-boundary.md)

## Purpose

Define a hardware-neutral interface for candidate evaluation, batch VM
execution, search, and verification. Compiler and verifier code must not depend
directly on CUDA APIs.

## Proposed Model

This record defines the contract that implementation must satisfy for
`replaceable-accelerator-boundary`. The implementation may change internal
representation or language choices without changing the observable behavior,
trust boundary, or ownership rules stated by its governing decisions.

## Invariants

- Compiler/verifier code depends on a hardware-neutral capability contract;
  CUDA/AMD/CPU adapters can be substituted without changing compiler semantics
  or candidate validity rules.
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
