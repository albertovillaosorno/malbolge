# Malbolge layout and encoding backend

## Status

Active

## Purpose

Implement address-sensitive instruction layout, self-modification planning,
encoding, jumps, data placement, runtime linkage, and final `.malbolge`
emission.

## Scope

This document governs the following declared TODO scope:

- `compiler/`
- `src/`
- `tests/compiler/`

## Current Behavior

### Implemented linear code-layout slice

`src/compiler/malbolge-layout/composition/lib.rs` owns an initial bounded
position-sensitive source encoder for exact profile `InputWord`, `OutputByte`,
`NoOperation`, and terminal `Halt` instructions. The encoder assigns code
addresses from zero, inverts the canonical VM instruction decoder over all 94
printable graphical cells for every target address, requires one unambiguous
encoding, and re-admits the entire byte stream independently before returning
it. The result preserves the immutable selected profile ID and fingerprint.

This slice admits 2..4096 code cells, one final halt, no earlier halts, and no
jumps, mutable code-state revisits, data placement, guest helper invocation,
or arbitrary ternary-IR scalar realization. Ordinary VM post-instruction code
encryption remains part of the normal execution semantics; these straight-line
instructions never revisit an earlier code address. There is no claim of
C-to-`.malbolge` compilation or general self-modifying layout yet.

`tests/malbolge_layout.rs` checks both current and historical profile decoders
across all 94 code-position phases, runs the resulting byte streams through
the normative `ProfileMachine` with real guest byte I/O and halt, and rejects
short, oversized, nonterminal, premature-halt, wrong-profile, truncated, and
modified source evidence.

### Remaining implementation

Map admitted typed ternary operations and runtime/heap helpers onto real target
instructions, solve data and code placement with self-modification constraints,
handle jumps/calls and control-flow labels, prove admissibility and runtime
behavior of complete code-state transitions, and publish verified final capsule
or raw `.malbolge` artifacts with source maps. This work remains active.

## Invariants

- Layout solves address-sensitive decode and self-modification constraints
  reproducibly and emits only verifier-accepted `.malbolge` for the declared
  profile.
- The stage has deterministic input/output form, rejects malformed or
  unsupported input explicitly, and preserves source/profile provenance needed
  downstream.

## Failure Behavior

Malformed IR, unsatisfied proof obligations, impossible layout, or unsupported
profile requirements fail closed before emitting accepted target code.

## Verification

- Expected durable artifact surface: `compiler/`, `src/`, `tests/compiler/`.
- Required evidence: golden/round-trip or normalized stage fixtures,
  deterministic hashes where promised, and end-to-end lowering regression cases.
- Prerequisite completion evidence: `ternary-machine-lowering`,
  `canonical-malbolge-target-profile`.
## References

- [Compiler Pipeline And Guest
  Runtime](../adr/compiler-pipeline-and-guest-runtime.md)
- [Deterministic C Surface And Clang
  Tooling](../adr/deterministic-c-surface-and-clang-tooling.md)
- [Verification Trust Boundary](../adr/verification-trust-boundary.md)

### Governing ADR Paths

- `docs/technical/adr/compiler-pipeline-and-guest-runtime.md`
- `docs/technical/adr/deterministic-c-surface-and-clang-tooling.md`
- `docs/technical/adr/verification-trust-boundary.md`
