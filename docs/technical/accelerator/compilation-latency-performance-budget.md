# Compilation latency performance budget

- Status: Proposed
- Planning identity: `compilation-latency-performance-budget`
- Last reviewed: 2026-07-26

## Governing Decisions

- [Replaceable Accelerator And Algorithm
  Ports](../adr/replaceable-accelerator-and-algorithm-ports.md)
- [Verification Trust Boundary](../adr/verification-trust-boundary.md)

## Purpose

Establish measured compile-time budgets aimed at seconds for cached or common
programs and bounded practical times for novel complex searches on capable GPUs.
Treat "seconds, not hours" as an engineering target backed by benchmarks rather
than an unverified promise.

## Proposed Model

This record defines the contract that implementation must satisfy for
`compilation-latency-performance-budget`. The implementation may change internal
representation or language choices without changing the observable behavior,
trust boundary, or ownership rules stated by its governing decisions.

## Invariants

- Compile-time budgets are expressed per workload/difficulty/resource class and
  report cold, warm-cache, synthesis, verification, and stitching costs rather
  than one opaque total.
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
