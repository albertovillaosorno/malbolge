# Canonical Malbolge target profile

- Status: Proposed
- Planning identity: `canonical-malbolge-target-profile`
- Last reviewed: 2026-07-26

## Governing Decisions

- [Specification Authority And Malbolge
  Evolution](../adr/specification-authority-and-malbolge-evolution.md)

## Purpose

Define `malbolge.json` as the single target-profile authority consumed by the
VM, compiler, tidy plugin, verifier, optimizer, runtime, and accelerators.

## Proposed Model

This record defines the contract that implementation must satisfy for
`canonical-malbolge-target-profile`. The implementation may change internal
representation or language choices without changing the observable behavior,
trust boundary, or ownership rules stated by its governing decisions.

## Invariants

- `malbolge.json` has a closed, versioned schema whose values are consumed
  consistently by VM, compiler, verifier, tidy, runtime, and optimization paths.
- The authoritative rule/specification is deterministic, versionable, and does
  not depend on undocumented host behavior.

## Failure Behavior

Missing authority or contradictory configuration fails closed rather than
selecting an implicit repository policy.

## Verification

- Expected durable artifact surface: `malbolge.json`,
  `docs/technical/specification/`, `compatibility/`.
- Required evidence: reviewed authority text plus deterministic
  parser/schema/governance tests for the declared boundary.

## Implementation Status

Not implemented. This proposed contract does not claim executable support yet.
