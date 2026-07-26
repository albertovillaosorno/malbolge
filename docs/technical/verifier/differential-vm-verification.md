# Differential VM verification

- Status: Proposed
- Planning identity: `differential-vm-verification`
- Last reviewed: 2026-07-26

## Governing Decisions

- [Verification Trust Boundary](../adr/verification-trust-boundary.md)

## Purpose

Run specification fixtures through the Rust VM, independent C VM, and
accelerator VM and compare output, termination, state, mutation, and instruction
traces. Run the original C interpreter only on the documented agreement subset
as historical differential evidence.

## Proposed Model

This record defines the contract that implementation must satisfy for
`differential-vm-verification`. The implementation may change internal
representation or language choices without changing the observable behavior,
trust boundary, or ownership rules stated by its governing decisions.

## Invariants

- The Rust VM, independent C VM, and any accelerator VM agree with the normative
  specification on all admitted classic fixtures. The historical interpreter
  participates only for fixtures whose behavior is defined and documented to
  agree with the specification.
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
