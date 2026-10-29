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
`RotateData`, `CrazyData`, one optional `RelocateDataPointer` after the
jump-free or forward-jump prefix, and terminal `Halt`. The encoder
assigns code positions from zero and inverts the normative VM instruction
decoder over all 94 graphical source bytes,
requires exactly one encoding at each address, and independently re-admits
the emitted source with canonical profile ID and fingerprint.

This slice requires two to 4096 code cells and one final halt. It admits
a sequence of strictly forward code jumps before a terminal halt.
Rotate/crazy are admitted only after one `j` data-pointer relocation;
earlier instructions may perform no-op, raw byte I/O, or strictly forward
jumps, but not data mutation. After a jump `D` and `C` diverge, so the
relocation base is read from the **current data-pointer memory cell**, not
the original encoded `j` source byte. The verifier replays prior XLAT2
mutation of source-memory cells before checking that the resulting base is
at least the complete emitted source length. This exact bound keeps all
later rotate/crazy writes disjoint from source code. Later jumps, duplicate
or unreachable relocations, early arithmetic, and overlapping bases reject.

A real VM boundary regression selects a later inverse-decode phase with a
greater encoded data address than position zero, admits a longer safe layout
including rotate/crazy, compares every code-position/encryption witness, and
rejects an otherwise identical layout extended one cell past the bound.
An exhaustive phase matrix independently rechecks every safely placeable
rotate/crazy opcode between positions 1 and 93 for both canonical profiles,
including the exact output phase and the execution/encryption witness sizes.

Forward code jumps (`i`) are admitted only **before** any data-pointer
relocation or rotate/crazy operation. The first jump reads its own code cell
through `D == C`; after it jumps, `D` and `C` diverge. Every later jump reads
through the evolving data pointer instead, so its target **cannot** be
inferred from the jump's own graphical code cell. The independent validator
tracks an exact bounded source-memory shadow, applying canonical XLAT2 after
each step at the real encryption address (`target - 1` for `i`, fetched code
position otherwise). It accepts each claimed post-increment target only when
that exact **current** data word plus one matches; targets must be forward and
inside the output source. All skipped code cells must be no-op padding, so no
future instruction is silently lost, and executed code is never revisited.

The admitted artifact retains three aligned deterministic execution witnesses:
code-pointer positions, data-pointer positions and post-step code encryption
addresses. The VM regression checks those positions step by step plus the
actual encrypted memory word, including relocated rotate/crazy geometry.
Real current/historical VM programs prove two forward jumps whose second
target is read from skipped no-op data, then three jumps where the final
target reads a **previously encrypted** no-op operand. Adversarial tests
reject forged later targets, backward destinations and effectful skipped
regions. A distinct real VM witness now executes one forward jump followed by a
`j` relocation, rotate and crazy; another fixture reads a `j` operand from
the earlier jump's **encrypted** target-minus-one cell. Independent source
extension beyond that dynamic operand rejects as unsafe. The actual CLI
emits both raw and versioned capsule files, reopened and run under both
canonical VMs to confirm byte I/O and guest memory mutation.

Another real VM regression demonstrates the distinct case where a
later jump reads a code cell whose normal no-op execution already encrypted
it. This evidence is not arbitrary branch lowering, a general data
memory-write proof, or unbounded semantic equivalence.

`tests/malbolge_layout.rs` exercises 94 decode phases for profile byte I/O,
executes real byte I/O, early and later-phase relocated rotate/crazy, and
single and multi-forward-jump skip programs under the canonical normative
`ProfileMachine`. It rejects malformed lengths, halts, profile identity,
altered source and aliasing placements.

This is a *first machine-code slice*, not C-to-`.malbolge` compilation:
no guest data/global layout, general IR lowering, backward code jumps,
code-state revisits, calls or runtime linkage is implemented yet.

### First real source-artifact publication

A dedicated `malbolge_layout` Cargo executable now accepts an exact canonical
`--profile`, an explicitly fresh `.malbolge` output path, and a bounded closed
list of machine-op tokens (`nop`, `input`, `output`, `rotate`, `crazy`,
`relocate`, `halt`, or `jump:<target>`). This is not a substitute for typed
ternary or C lowering. It invokes the same verified position-sensitive layout
encoder, separately re-admits the complete emitted bytes, and loads/runs the
result under the selected normative `ProfileMachine` with empty input. A halt
must occur at the exact admitted execution-witness step count before the
source is published.

The publisher creates a new same-directory staging file, flushes/syncs and
reopens its exact graphical bytes, then uses a no-overwrite hard link to
atomically reveal only a complete final `.malbolge`. Existing targets and
symlinks are never replaced; invalid profiles, operands, paths or layout
shapes fail closed. Process-level integration tests execute the built binary,
reopen emitted files under historical/current canonical profiles with real
byte input, test forward jumps and relocated arithmetic, compare exact output
bytes across independent runs, reject unsupported input and symlinks, and
exercise concurrent writers to one target. A separate three-jump external
process fixture publishes both raw and capsule sources under both profiles,
reopens and executes the exact outputs, and rejects a forged later destination
without creating a final file. On abrupt interruption a hidden
staging file may remain; it cannot expose a partial final target.

An optional `--capsule` mode now wraps verified raw source using the
existing version-one historical-fallback capsule builder. The producer
independently parses the result before publication and requires an exact
canonical profile identity/fingerprint and byte-for-byte payload equality.
Real external-process integration invokes the *general* `malbolge` runner on
a modern-profile capsule, and separately runs the historical-safe fallback
through the classic interpreter. The unframed raw mode remains unchanged:
modern raw `.malbolge` alone carries no profile and needs an explicitly
selected profile-aware loader. Neither mode implements source maps, general
C/ternary lowering or guest-runtime linkage.

### Canonical ternary-IR-to-file bridge

The separate `byte-echo-bridge` now connects to the same artifact publisher
using `--ternary-file <canonical-MCTR-file>` after the CLI's `--` delimiter.
The input must be a regular nonempty file of at most 1 MiB. The publisher
uses the canonical MCTR version-one restorer, not a permissive ad hoc decoder,
and calls the independently validated bridge to admit one exact
successful-byte-input/output SSA echo trace with a final void return. The
bridge, not the file publisher, owns all semantic effect restrictions.

The resultant graphical Malbolge bytes receive the existing normative-profile
VM load/halt check and either raw or version-one capsule publication with
independently validated identity/payload and atomic no-overwrite behavior.
End-to-end tests invoke the real binary with a serialized canonical ternary
program, reopen both types of output under the normative VM, and compare
an actual multi-byte echo trace (including zero and 255). For this ternary
subset the publisher also replays two fixed successful-byte input patterns
on the normative VM, requiring byte-exact output, consumed-byte count and
witness-length termination before publication. Forged profiles, corrupted
wire bytes, valid but unsupported SSA output, missing or oversized inputs,
extra operands and existing targets fail without a new final artifact.
The source hash in MCTR is copied provenance, not independent source
authentication; VM preflight with empty input verifies
termination, and two chosen successful-byte traces are only bounded evidence,
**not** total successful byte-I/O equivalence including EOF.

This is a **bounded, working ternary-stage-to-file path**, but it does not
admit arbitrary ternary operations, source-C programs, guest heap, ABI return
values, EOF, failed I/O, or unbounded control-flow/layout code-state revisits.

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
