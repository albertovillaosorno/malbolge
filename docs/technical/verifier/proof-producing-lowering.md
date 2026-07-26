# Proof-producing lowering

- Status: Proposed
- Planning identity: `proof-producing-lowering`
- Last reviewed: 2026-07-26

## Governing Decisions

- [Verification Trust Boundary](../adr/verification-trust-boundary.md)

## Purpose

Investigate compiler outputs carrying compact witnesses or proof material for
local equivalence claims so final acceptance need not trust CUDA, PyTorch,
stochastic search, or superoptimization implementations.

## Proposed Model

This record defines the contract that implementation must satisfy for
`proof-producing-lowering`. The implementation may change internal
representation or language choices without changing the observable behavior,
trust boundary, or ownership rules stated by its governing decisions.

## Invariants

- Selected lowering steps emit compact proof/equivalence evidence that a smaller
  trusted checker can validate independently of the optimizer and code generator
  that produced it.
- The verifier is tested against valid cases and deliberately mutated invalid
  cases so acceptance and rejection boundaries are evidenced independently.

## Failure Behavior

Unknown or unproved equivalence is rejection or an explicitly bounded result,
never implicit acceptance.

## Verification

- Expected durable artifact surface: `verifier/`, `tests/differential/`,
  `tests/exhaustive/`, `tests/fuzz/`.
- Required evidence: known-valid fixtures, seeded invalid mutations,
  counterexamples for rejected candidates, and deterministic replay.

## Implementation Status

Not implemented. This proposed contract does not claim executable support yet.
