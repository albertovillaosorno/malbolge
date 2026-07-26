# Historical-Interpreter Fallback Capsule

- Status: Proposed
- Planning identity: `historical-interpreter-fallback-capsule`
- Last reviewed: 2026-07-26

## Governing Decisions

- [Specification Authority And Malbolge
  Evolution](../adr/specification-authority-and-malbolge-evolution.md)

## Purpose

Design an extended `.malbolge` container recognized by modern runtimes while the
1998 interpreter sees only a small historical fallback program, ideally by using
whitespace metadata that the original loader ignores.

## Proposed Model

The modern runtime recognizes a versioned whitespace sideband containing target
profile identity and extended payload information. A historical interpreter,
which ignores that sideband, sees only an ordinary legacy fallback program.

The fallback exists to explain that the artifact requires a newer runtime. It is
not evidence that the extended program is semantically compatible with Ben
Olmstead's implementation.

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

- A modern runtime must parse and validate the extension sideband exactly.
- The historical interpreter must ignore the sideband and execute only the
  fallback for representative capsules.
- Specification-conformant classic programs remain ordinary non-capsule
  `.malbolge` when no extension is required.

## Implementation Status

Not implemented.
