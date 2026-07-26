# Historical Malbolge semantics specification

- Status: Proposed
- Planning identity: `historical-malbolge-semantics-specification`
- Last reviewed: 2026-07-26

## Governing Decisions

- [Historical Compatibility And Malbolge
  Evolution](../adr/historical-compatibility-and-malbolge-evolution.md)

## Purpose

Specify the original 1998 machine: 59,049 ten-trit words, registers, decoding,
crazy operation, rotation, self-encryption, input/output, wraparound, loading,
and termination behavior.

## Proposed Model

This record defines the contract that implementation must satisfy for
`historical-malbolge-semantics-specification`. The implementation may change
internal representation or language choices without changing the observable
behavior, trust boundary, or ownership rules stated by its governing decisions.

## Invariants

- The specification defines loader behavior, registers, memory, instruction
  decode, crazy operation, rotate, I/O, self-encryption, increments/wrap, and
  halt/error behavior as explicit state transitions.
- The authoritative rule/specification is deterministic, versionable, and does
  not depend on undocumented host behavior.

## Failure Behavior

Missing authority or contradictory configuration fails closed rather than
selecting an implicit repository policy.

## Verification

- Expected durable artifact surface: `tools/malbolge/`,
  `docs/technical/specification/`, `docs/technical/specification/mathematics/`.
- Required evidence: reviewed authority text plus deterministic
  parser/schema/governance tests for the declared boundary.

## Implementation Status

Not implemented. This proposed contract does not claim executable support yet.
