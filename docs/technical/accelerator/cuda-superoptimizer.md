# CUDA superoptimizer

- Status: Proposed
- Planning identity: `cuda-superoptimizer`
- Last reviewed: 2026-07-26

## Governing Decisions

- [Replaceable Accelerator And Algorithm
  Ports](../adr/replaceable-accelerator-and-algorithm-ports.md)
- [Verification Trust Boundary](../adr/verification-trust-boundary.md)

## Purpose

Implement GPU-parallel candidate synthesis, pruning, equivalence testing, cost
evaluation, and verified block stitching.

## Proposed Model

This record defines the contract that implementation must satisfy for
`cuda-superoptimizer`. The implementation may change internal representation or
language choices without changing the observable behavior, trust boundary, or
ownership rules stated by its governing decisions.

## Invariants

- GPU candidate generation/evaluation can be disabled without changing
  correctness, and every returned winning block is revalidated by the trusted
  verifier before catalog or compiler admission.
- A CPU/reference path remains sufficient for correctness, and accelerator
  failure/unavailability changes performance rather than semantic acceptance.
- Performance conclusions use equivalent workloads and report raw-sample
  provenance, resource budgets, dispersion/uncertainty, and failure/success
  behavior rather than only a best-case number.

## Failure Behavior

Missing hardware, resource exhaustion, or accelerator disagreement falls back or
fails explicitly without changing correctness rules.

## Verification

- Expected durable artifact surface: `accelerator/`, `algorithms/`,
  `optimizer/`, `benchmarks/accelerator/`, `tests/optimizer/`.
- Required evidence: CPU/reference differential results, device/resource
  metadata, failure/fallback tests, and benchmark samples for claimed speedups.
- Performance evidence pending: raw measurements plus a reproducible
  scaling/statistical summary tied to exact workload and hardware/software
  identity.

## Implementation Status

Not implemented. This proposed contract does not claim executable support yet.
