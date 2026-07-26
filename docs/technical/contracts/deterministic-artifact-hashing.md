# Deterministic cross-backend artifact hashing

- Status: Proposed
- Planning identity: `deterministic-cross-backend-artifact-hashing`
- Last reviewed: 2026-07-26

## Governing Decisions

- [Compiler Pipeline And Guest
  Runtime](../adr/compiler-pipeline-and-guest-runtime.md)
- [Verification Trust Boundary](../adr/verification-trust-boundary.md)

## Purpose

Require byte-identical outputs and hashes across backends for declared
deterministic workloads, including versioned example artifacts and compiler-
produced `.malbolge` artifacts where deterministic builds are promised.

## Proposed Model

This record defines the contract that implementation must satisfy for
`deterministic-cross-backend-artifact-hashing`. The implementation may change
internal representation or language choices without changing the observable
behavior, trust boundary, or ownership rules stated by its governing decisions.

## Invariants

- For builds promised deterministic, CPU/GPU/optimizer/execution choices yield
  byte-identical committed artifacts or a documented normalization rule whose
  canonical hash is identical.
- The end-to-end fixture demonstrates the intended behavior from admitted
  source/input through the actual generated/executed Malbolge path.

## Failure Behavior

Missing external inputs or unmet target capabilities fail explicitly;
demonstrations may not substitute host logic for guest behavior.

## Verification

- Expected durable artifact surface: `docs/technical/examples/`,
  `tests/applications/`, `benchmarks/applications/`, `runtime/`.
- Required evidence: reproducible build/run commands, expected outputs or
  interaction traces, artifact hashes, and end-to-end verification.

## Implementation Status

Not implemented. This proposed contract does not claim executable support yet.
