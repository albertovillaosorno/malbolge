# Reusable block catalogue

## Status

Proposed

## Purpose

Build a deterministic catalogue of verified arithmetic, branch, memory, calling
convention, and runtime blocks so recurring semantics can be reused instead of
resynthesized. Catalogue entries also serve as linkable semantic units with
explicit state, layout, and self-modification contracts.

## Scope

This document governs the following declared TODO scope:

- `accelerator/`
- `algorithms/`
- `optimizer/`
- `benchmarks/accelerator/`
- `tests/optimizer/`

## Current Behavior

### Proposed Model

Each catalogue entry is addressed by stable semantic identity rather than raw
text bytes. The entry contains pre/postconditions, entry/exit machine state,
target profile, layout assumptions, mutation footprint, cost metrics,
provenance,
and verifier identity. The linker may reuse an entry only when the complete
composition contract matches its current obligations.

### Implementation Status

Not implemented. No reusable block is currently promoted as repository
architecture merely because an experiment produced one.

## Invariants

- Every admitted entry has independent verifier evidence.
- Catalogue lookup cannot weaken address, encryption, mutation, or
  target-profile
  constraints.
- Equivalent semantics may have multiple cost-specialized implementations; the
  selected implementation and cost model remain explicit.
- CPU/reference correctness is sufficient even when accelerator-backed catalogue
  construction is unavailable.

## Failure Behavior

Missing or stale verifier evidence, incompatible state/layout assumptions, or
unknown mutation effects make an entry ineligible for reuse. The compiler falls
back to another verified implementation or fresh synthesis rather than forcing a
near match.

## Verification

- Deterministic catalogue identities survive rebuilds from identical evidence.
- Positive and negative linker fixtures exercise exact contract matching.
- Cross-backend tests compare catalogue construction and lookup results where
  deterministic equivalence is promised.
- Catalogue-hit benchmarks are reported separately from fresh synthesis cost.

## References

- [Replaceable Accelerator And Algorithm
  Ports](../../adr/replaceable-accelerator-and-algorithm-ports.md)
- [Verification Trust Boundary](../../adr/verification-trust-boundary.md)
- [State-aware Malbolge linker](../../compiler/state-aware-malbolge-linker.md)

### Governing ADR Paths

- `docs/technical/adr/replaceable-accelerator-and-algorithm-ports.md`
- `docs/technical/adr/verification-trust-boundary.md`
