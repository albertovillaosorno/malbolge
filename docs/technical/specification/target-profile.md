# Canonical Malbolge target profile

## Status

Accepted implementation

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
- `src/automation/repository/composition/scripts/validate/target_profile.py`
- `tests/test_target_profile.py`

## Current Behavior

### Proposed Model

This record defines the contract that implementation must satisfy for
`canonical-malbolge-target-profile`. The implementation may change internal
representation or language choices without changing the observable behavior,
trust boundary, or ownership rules stated by its governing decisions.

### Implementation Status

Schema version 2 is implemented in repository-root `malbolge.json`. It contains
an immutable `malbolge-1998` historical-conformance profile, retains
`malbolge-2026.1`, `malbolge-2026.2`, and `malbolge-2026.3` as immutable
versioned identities, and selects the year-only `malbolge-2026` as
the current language profile. The current profile
uses the scalable 14-trit single-word ternary geometry defined by the
scalable-memory contract: 4,782,969 word values and the same number of directly
addressed memory words.

I/O opcode assignment is versioned profile semantics. `malbolge-1998` and the
current `malbolge-2026` use interpreter-compatible `/` input and `<` output.
The already published `malbolge-2026.1` and `malbolge-2026.2` identities retain
their specification-first `<` input and `/` output assignment. The published
`malbolge-2026.3` compatibility identity retains the same interpreter-compatible
I/O and geometry as the annual current profile, but remains a distinct immutable
artifact identity. The current
profile does not inherit historical C undefined behavior, non-progress as a
modern termination policy, or the ten-trit resource ceiling merely because its
I/O is source-compatible with the original interpreter.

`src/automation/repository/composition/scripts/validate/target_profile.py`
provides a dependency-free closed-schema
validator using duplicate-key-rejecting JSON parsing. It enforces exact schema
keys, ternary word consistency, single-word memory consistency, EOF at the
maximum profile word, the frozen 1998 machine envelope, exactly one selected
current identity, preservation of the sequential deterministic
self-modifying semantic core across schema-v2 profiles, and an exact
one-to-one assignment of `<` and `/` to versioned input/output roles.

Cross-component consumption is not complete. The classic safe Rust `Machine`
remains deliberately bound to `malbolge-1998` and cannot silently execute a
`malbolge-2026` artifact. `ProfileMachine`, native execution, CUDA geometry,
decompiler output, runtime capability checks, and current-profile performance
workloads consume canonical descriptors, generated projections, or the typed
`current_profile_geometry()` view. Compiler, tidy, and integrated verifier
consumers remain future implementations and must adopt this authority within
their own typed work before they execute or publish profile-bound artifacts.

Published profile identity is additionally bound by `malbolge-profile-v1`
fingerprints. The fingerprint includes profile ID/version, target schema,
word/memory geometry, and semantics, but excludes the registry-only `kind` role
so current-to-versioned lifecycle changes cannot mutate old artifact identity.
Canonical fingerprints are generated into
`src/interoperability/profile-compatibility/contract/profile-fingerprints.json`
and the Rust profile projection.

## Invariants

- `malbolge.json` has a closed, versioned schema whose values are consumed
  consistently by VM, compiler, verifier, tidy, runtime, and optimization paths.
- Every authoritative profile rule is deterministic, versionable, and excludes
  undocumented host behavior.
- `malbolge-1998` identifies defined, reproducible original-interpreter
  semantics in the ten-trit/59,049-word envelope and remains available for
  conformance and
  archaeology.
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
  `src/automation/repository/composition/scripts/validate/target_profile.py`,
  `tests/test_target_profile.py`.
- Executable schema checks: `python
  src/automation/repository/composition/scripts/validate/target_profile.py` and
  `.dependencies/python/3.14.6/Scripts/pytest-jig.cmd -c
  .jig/lang/python/pytest.ini
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
