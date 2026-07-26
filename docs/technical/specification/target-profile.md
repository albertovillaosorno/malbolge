# Canonical Malbolge target profile

## Status

Active implementation

## Purpose

Define `malbolge.json` as the single target-profile authority consumed by the
VM, compiler, tidy plugin, verifier, optimizer, runtime, and accelerators.
The authority distinguishes frozen historical conformance from the versioned
current Malbolge language.

## Scope

This document governs the following declared TODO scope:

- `malbolge.json`
- `docs/technical/specification/`
- `compatibility/`
- `scripts/validate/target_profile.py`
- `tests/test_target_profile.py`

## Current Behavior

### Proposed Model

This record defines the contract that implementation must satisfy for
`canonical-malbolge-target-profile`. The implementation may change internal
representation or language choices without changing the observable behavior,
trust boundary, or ownership rules stated by its governing decisions.

### Implementation Status

Schema version 1 is implemented in repository-root `malbolge.json`. It contains
an immutable `malbolge-1998` historical-conformance profile and selects
`malbolge-2026.1` as the first explicit current-language identity. The current
profile intentionally has the same ten-trit/59,049-word executable envelope as
the historical profile until the scalable-memory TODO resolves the larger
addressing model. The separate identity is nevertheless mandatory: future
profiles advance `current_profile` instead of mutating old artifact semantics.

`scripts/validate/target_profile.py` provides a dependency-free closed-schema
validator using duplicate-key-rejecting JSON parsing. It enforces exact schema
keys, ternary word consistency, single-word memory consistency, the frozen 1998
machine envelope, distinct current identity, and the schema-v1 sequential,
deterministic, self-modifying semantic core. Standard-library tests exercise
positive and fail-closed cases.

Cross-component consumption is not complete. The existing VM still implements
its 1998-profile constants directly and compiler/tidy/runtime consumers are not
yet universally profile-driven, so this contract remains active.

## Invariants

- `malbolge.json` has a closed, versioned schema whose values are consumed
  consistently by VM, compiler, verifier, tidy, runtime, and optimization paths.
- The authoritative rule/specification is deterministic, versionable, and does
  not depend on undocumented host behavior.
- `malbolge-1998` exactly identifies the written 1998 ten-trit/59,049-word
  machine and remains available for conformance and archaeology.
- The canonical current profile is a versioned evolution of Malbolge, not a
  separately branded "extended" language. It may remove historical resource
  ceilings while preserving the defining ternary/self-modifying semantics.
- Every artifact records its exact profile identity; no component silently
  assumes that current-language output is valid under `malbolge-1998`.

## Failure Behavior

Missing authority or contradictory configuration fails closed rather than
selecting an implicit repository policy.

## Verification

- Expected durable artifact surface: `malbolge.json`,
  `docs/technical/specification/`, `compatibility/`,
  `scripts/validate/target_profile.py`, `tests/test_target_profile.py`.
- Executable schema checks: `python scripts/validate/target_profile.py` and
  `python -m unittest tests/test_target_profile.py`.
- Required evidence: reviewed authority text plus deterministic
  parser/schema/governance tests for the declared boundary.
- Prerequisite completion evidence:
  `historical-malbolge-semantics-specification`,
  `historical-undefined-behavior-catalogue`.
## References

- [Specification Authority And Malbolge
  Evolution](../adr/specification-authority-and-malbolge-evolution.md)

### Governing ADR Paths

- `docs/technical/adr/specification-authority-and-malbolge-evolution.md`
