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

`src/compiler/malbolge-layout/composition/lib.rs` owns a bounded position-
sensitive source encoder for profile `InputWord`, `OutputByte`, `NoOperation`,
`RotateData`, `CrazyData`, a single optional `RelocateDataPointer` prologue,
one source-cell-derived `JumpForward`, and terminal `Halt`. The encoder
assigns code positions from zero and inverts the normative VM instruction
decoder over all 94 graphical source bytes,
requires exactly one encoding at each address, and independently re-admits
the emitted source with canonical profile ID and fingerprint.

This slice requires two to 4096 code cells and one final halt. It admits at
most one strictly forward code jump before a terminal halt. Rotate/crazy are
admitted only after one `j` data-pointer relocation; earlier instructions
may perform no-op or raw machine I/O, but no jump or data mutation. Before
that relocation `D == C`, so the originally encoded graphical code cell at
the relocation's chosen address becomes the new data base. The exact cell
value must be at least the complete emitted source length. The checked
offset keeps all later data mutations disjoint from source-code cells.
Missing, duplicate, or potentially overlapping relocations fail closed.

A real VM boundary regression selects a later inverse-decode phase with a
greater encoded data address than position zero, admits a longer safe layout
including rotate/crazy, compares every code-position/encryption witness, and
rejects an otherwise identical layout extended one cell past the bound.
An exhaustive phase matrix independently rechecks every safely placeable
rotate/crazy opcode between positions 1 and 93 for both canonical profiles,
including the exact output phase and the execution/encryption witness sizes.

The forward jump (`i`) is admitted only without data-pointer relocation: at
that moment the data pointer still equals the code pointer, so the jump reads
its own *original graphical source cell* and sets the next code pointer to
that byte plus one. The claimed target must be strictly forward and within
emitted source length; every skipped cell is an inert `NoOperation` and no
second jump may occur. The VM post-step encryption of `target - 1` cannot
corrupt reachable instructions. The verifier re-derives the target from the
unique encoded byte and rejects any forged or backward target, effectful
gap, or jump mixed with relocated arithmetic.

The admitted artifact additionally retains an exact bounded execution witness
of reachable code positions and post-step code-encryption targets. Ordinary
steps encrypt their fetched code position, while `i` encrypts `target - 1`
and terminal `v` encrypts nothing. The checker derives these positions from
the independently admitted operation shape, with no runtime guest execution.
Current and historical VM tests replay the exact path and compare every
post-step XLAT2 memory update to this proof, including the noncontiguous
jump and relocated arithmetic paths. This witness is **not** a proof of
arbitrary input/output equivalence or all runtime memory mutations.

`tests/malbolge_layout.rs` exercises 94 decode phases for profile byte I/O,
executes real byte I/O, early and later-phase relocated rotate/crazy, and
first forward-jump skip programs under the current and historical normative
`ProfileMachine`. It rejects malformed lengths, halts, profile identity,
altered source and aliasing placements.

This is a *first machine-code slice*, not C-to-`.malbolge` compilation:
no guest data/global layout, general IR lowering, backward code jumps,
code-state revisits, calls or runtime linkage is implemented yet.

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
