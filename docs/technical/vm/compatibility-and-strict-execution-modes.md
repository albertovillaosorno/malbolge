# Compatibility and strict execution modes

- Status: Proposed
- Planning identity: `compatibility-and-strict-execution-modes`
- Last reviewed: 2026-07-26

## Governing Decisions

- [Historical Compatibility And Malbolge
  Evolution](../adr/historical-compatibility-and-malbolge-evolution.md)
- [Verification Trust Boundary](../adr/verification-trust-boundary.md)

## Purpose

Provide a compatibility mode that reproduces meaningful historical quirks and a
strict mode that turns formerly undefined or pathological situations into
explicit diagnostics without changing the compatibility target for well-defined
programs.

## Proposed Model

This record defines the contract that implementation must satisfy for
`compatibility-and-strict-execution-modes`. The implementation may change
internal representation or language choices without changing the observable
behavior, trust boundary, or ownership rules stated by its governing decisions.

## Invariants

- Compatibility mode preserves meaningful defined historical behavior, while
  strict mode converts pathological/undefined situations into deterministic
  diagnostics without changing well-defined programs.
- Observable state, I/O, termination, and diagnostics match the declared
  semantic profile across positive, boundary, and adversarial fixtures.

## Failure Behavior

Invalid programs, unsupported profiles, or broken native assumptions fail
deterministically without changing guest-visible state silently.

## Verification

- Expected durable artifact surface: `vm/`, `execution/`, `tests/vm/`,
  `benchmarks/interpreter/`.
- Required evidence: semantic fixtures, state/I/O traces where diagnostic, and
  differential results against the applicable oracle/reference implementation.

## Implementation Status

Not implemented. This proposed contract does not claim executable support yet.
