# Historical-Interpreter Fallback Capsule

## Status

Proposed

## Purpose

Design an extended `.malbolge` container recognized by modern runtimes while the
1998 interpreter sees only a small historical fallback program, ideally by using
whitespace metadata that the original loader ignores.

## Scope

This document governs the following declared TODO scope:

- `compatibility/`
- `docs/technical/specification/`
- `tests/compatibility/`

## Current Behavior

### Proposed Model

The modern runtime recognizes a versioned whitespace sideband containing target
profile identity and extended payload information. A historical interpreter,
which ignores that sideband, sees only an ordinary legacy fallback program.

The fallback exists to explain that the artifact requires a newer runtime. It is
not evidence that the extended program is semantically compatible with Ben
Olmstead's implementation.

### Implementation Status

Not implemented.

## Invariants

- Modern runtimes validate the capsule deterministically before executing its
  extended payload.
- The old interpreter sees only the deliberately authored fallback surface.
- The extended payload follows the normative modern target specification.
- Any fallback instruction behavior that depends on a Ben-interpreter defect is
  isolated to that fallback and never leaks into normal VM semantics.
- The artifact keeps the `.malbolge` extension and identifies the required
  target profile unambiguously.

## Failure Behavior

Malformed sideband data, unsupported profile identity, or integrity failure is a
deterministic modern-runtime error. Historical fallback behavior is best-effort
communication, not a semantic recovery path.

## Verification

- Expected durable artifact surface: `compatibility/`,
  `docs/technical/specification/`, `tests/compatibility/`.
- Required evidence: classic specification-conformance corpus plus
  extension/profile boundary fixtures and exact diagnostics.
- Prerequisite completion evidence: `malbolge-2-extended-memory-model`,
  `required-profile-diagnostics`.
## References

- [Specification Authority And Malbolge
  Evolution](../adr/specification-authority-and-malbolge-evolution.md)

### Governing ADR Paths

- `docs/technical/adr/specification-authority-and-malbolge-evolution.md`
