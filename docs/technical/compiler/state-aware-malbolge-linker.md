# State-aware Malbolge linker

## Status

Proposed

## Purpose

Define a linker for independently compiled Malbolge blocks whose correctness
accounts for symbols, absolute addresses, positional decoding, post-instruction
encryption, entry/exit machine state, and self-modification footprints. Linking
must be treated as semantic composition rather than byte concatenation.

## Scope

This document governs the following declared TODO scope:

- `compiler/linker/`
- `compiler/`
- `tests/compiler/`
- `math/specification/`

## Current Behavior

### Proposed Model

Each linkable block exposes a deterministic contract containing exported and
imported symbols, target profile, required entry state, guaranteed exit state,
address/layout constraints, mutation footprint, relocation obligations, and
verifier identity. The linker solves compatible placement and phase constraints,
then emits a candidate image plus evidence for independent verification.

The linker may reuse verified fixed-layout blocks, but relocation or stitching
is never accepted solely because bytes fit at the requested offsets.

### Implementation Status

Not implemented. This proposed contract does not claim linker support yet.

## Invariants

- Linking never weakens guest self-modification or encryption semantics.
- Every relocation-sensitive block identifies the assumptions that make its
  decode and self-encryption behavior valid at the selected address.
- Entry/exit register, memory, I/O, and mutation contracts are explicit enough
  for independent composition checking.
- Candidate layout and stitching are untrusted until the verifier accepts the
  composed artifact.
- Global code immutability is not introduced as a shortcut for composition.

## Failure Behavior

Unsatisfied symbol, state, phase, layout, mutation, or verification obligations
fail closed without emitting an accepted linked artifact. The linker reports the
smallest practical conflicting contract rather than silently falling back to
textual concatenation or unverified patching.

## Verification

- Golden fixtures cover independent blocks whose position changes decoding or
  self-encryption behavior.
- Negative fixtures cover incompatible entry/exit state, overlapping mutation
  footprints, impossible relocations, and stale verifier evidence.
- Translation-validation evidence compares each accepted linked artifact with
  the composed source/IR semantics.
- Repeated builds from identical inputs produce identical normalized link plans
  and target artifacts.

## References

- [Compiler Pipeline And Guest
  Runtime](../adr/compiler-pipeline-and-guest-runtime.md)
- [Verification Trust Boundary](../adr/verification-trust-boundary.md)
- [Malbolge layout and encoding
  backend](malbolge-layout-and-encoding-backend.md)

### Governing ADR Paths

- `docs/technical/adr/compiler-pipeline-and-guest-runtime.md`
- `docs/technical/adr/verification-trust-boundary.md`