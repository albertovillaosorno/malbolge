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

Schema version 2 is implemented in repository-root `malbolge.json`. It contains
an immutable `malbolge-1998` historical-conformance profile, retains the
`malbolge-2026.1` ten-trit transition identity, and selects `malbolge-2026.2` as
the current language profile. The current profile uses the scalable 14-trit
single-word ternary geometry defined by the scalable-memory contract:
4,782,969 word values and the same number of directly addressed memory words.

`scripts/validate/target_profile.py` provides a dependency-free closed-schema
validator using duplicate-key-rejecting JSON parsing. It enforces exact schema
keys, ternary word consistency, single-word memory consistency, EOF at the
maximum profile word, the frozen 1998 machine envelope, exactly one selected
current identity, and preservation of the sequential deterministic
self-modifying semantic core across schema-v2 profiles.

Cross-component consumption is not complete. The existing safe Rust VM still
implements `malbolge-1998` constants directly and must not silently execute a
`malbolge-2026.2` artifact. Compiler, tidy, verifier, runtime, and accelerator
consumers are not yet universally profile-driven, so this contract remains
active.

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
  `.dependencies/python/3.14.6/Scripts/pytest-jig.cmd -c pytest.ini
  tests/test_target_profile.py tests/compatibility/test_scalable_memory.py`.
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
