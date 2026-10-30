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

The admitted artifact retains four aligned deterministic execution witnesses:
code-pointer positions, data-pointer positions, post-step code encryption
addresses and optional rotate/crazy guest data-write addresses. The static
checker rejects each data-write address inside the emitted source region.
Normative traced VM steps independently check the write address against its
actual semantic data read and any changed-cell delta, including when a
write commits an unchanged value, as well as code XLAT2 encryption. This
proves the bounded address separation, **not** input-dependent guest values.
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

### Library-level automatic forward-jump padding

The independent encoder also exposes `encode_auto_padded_forward_layout` for
logical instruction sequences with symbolic forward-jump slots. It computes
the target from the live `D`-pointer memory shadow (including XLAT2 updates),
expands only safe no-op padding cells, records logical-to-source address
mapping, then calls the same exact-profile independent layout admission.
The returned `source_cell_origins` vector labels every physical graphical
cell with its original logical index, generated reached relocation no-op,
or skipped forward-jump no-op. This provenance is computed from an admitted
VM execution witness rather than assumed reachable positions; it does not
represent source-C line mapping.
The planner fails closed on nonforward targets, post-relocation jumps or
layout overflow. Real VMs exercise one-, two- and three-hop witnesses and
jump-then-data-relocation; the first-jump phase matrix covers all 94
address-sensitive decoder phases under both canonical profiles. The current
source CLI continues accepting explicit concrete `jump:TARGET` tokens by
default. An opt-in `--auto-layout` mode now accepts symbolic `jump` and
`auto-relocate` tokens, with the existing library planner as its untrusted
candidate producer. This is not conditional branch lowering or a general
guest code-state solver.

`PaddedForwardStep::AutoRelocate` additionally chooses the earliest safe
`j` placement among at most 94 reached source phases. It inserts reached
no-ops while checking dynamic `D` state, future source length and previous
XLAT2 encryptions, then delegates data nonalias proof to independent layout
admission. Tests execute actual current/historical VMs for long suffixes
and a two-hop jump plus relocation with rotate/crazy; impossible placements,
duplicate relocation and post-relocation jump attempts reject. This library
helper is available only in the opt-in symbolic CLI grammar, not the
default concrete-token mode.

### Opt-in symbolic layout artifact publisher

After the CLI `--` delimiter, `--auto-layout` chooses the symbolic input
mode. It accepts `jump` and `auto-relocate` together with the ordinary
bounded non-jump machine tokens, rejecting the numeric `jump:TARGET` token
and any ternary-file operand. The default concrete mode and both MCTR wire
modes are unchanged. Every parsed symbolic step uses the already verified
`encode_auto_padded_forward_layout` library planner. The emitted operation
plan and raw bytes are then **separately** passed to
`admit_linear_layout` with the exact selected profile fingerprint and ID;
only independently re-admitted code is sent to the normative VM and the
same raw/capsule no-overwrite publisher. The VM execution length is the
number of reached code steps, not the number of padded source characters.

External-process regressions compare raw/capsule output against the original
manual concrete layout for a first forward jump, a two-hop encrypted-data
operand plus `j`, and automatically placed `j` with real rotate/crazy.
Both 1998 and 2026 profile VMs replay the published source and check
successful I/O or data-pointer relocation.

An additional process-level test runs the actual general
`malbolge --input-stdin` command on the generated
historical raw source and modern version-one capsule, requiring exact
`0x00 0xff` output for two non-EOF guest inputs. A second general-runner
fixture proves a symbolic three-hop jump chain whose last target is read
from an already XLAT2-encrypted operand. Raw and capsule outputs match the
independent concrete-token source exactly; a normative VM witness verifies
the data cell changed to the expected encrypted word before the real
binary-input process replay. Unsupported symbolic shapes,
invalid arguments, and occupied paths fail without accepted new artifacts.
This is source layout for a closed machine subset, not general control flow,
source-C compilation, guest ABI, or total I/O equivalence.

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
An explicit `--latest-byte-trace --ternary-file <canonical-MCTR-file>` mode
extends this same checked file publisher to latest-read SSA traces with a
single void return. Each output must refer to the most recent successful
byte input; repeated output and consumed-but-unused input are allowed. The
original `--ternary-file` option stays strict adjacent echo, and the two
modes emit byte-identical raw/capsule artifacts on the echo intersection.
The publisher derives the exact expected output for each of two fixed
successful-byte input patterns from the validated ordered MCTR effects, then
compares the normative VM's output, consumed count and exact halting step.
Missing/wrong-profile/corrupt wire, stale SSA output after a later read and
misordered mode options reject before publication. A real external-process
fixture reloads both new artifact formats and independently verifies
repeated outputs and ignored inputs, including zero and byte 255.

The source hash in MCTR is copied provenance, not independent source
authentication; VM preflight with empty input verifies
termination, and two chosen successful-byte traces are only bounded evidence,
**not** total successful byte-I/O equivalence including EOF.

This is a **bounded, working ternary-stage-to-file path**, but it does not
admit arbitrary ternary operations, source-C programs, guest heap, ABI return
values, EOF, failed I/O, or unbounded control-flow/layout code-state revisits.

### Direct canonical typed-IR publication

The same `malbolge_layout` executable now exposes explicit `--typed-file`
mode for canonical `MCTI` version-one typed modules. The original default
continues accepting only one zero-argument void adjacent successful-byte
echo function. An opt-in `--latest-byte-trace --typed-file` mode supports
repeated output of the latest read and ignored intervening successful
inputs. Valid SSA output from an older overwritten read still rejects.
The file is checked as a regular nonempty bounded input at most 1 MiB,
restored via canonical typed-IR admission, projected/lowered by the existing
typed-echo adapter and independently encoded into canonical MCTR source.

The publisher does **not** trust the adapter's Malbolge layout directly:
it separately decodes the generated MCTR and uses the original ternary
byte-trace bridge to re-derive code, requiring identical bytes, execution
witness length and exact target-profile identity. It then applies its
ordinary normative VM reachability and two successful-byte I/O traces,
optional canonical capsule wrapping and atomic no-overwrite artifact
publication. Process tests compare strict and latest-read direct MCTI
output byte-for-byte against independent MCTR-file publication, reopen
published raw/capsule payloads and verify real VM output/consumption, and
reject malformed input, profile mismatch, stale-SSA use, oversize and
occupied output paths. A second integration test executes the directly
published MCTI capsule through the real `malbolge --input-stdin` process,
requiring exact repeated byte output for input 0, 255 and 128. Invalid
mode order, absent typed path and mixed trailing machine tokens are refused.
This closes one artifact-adapter integration gap, not arbitrary C lowering,
guest-runtime ABI, EOF or I/O failure semantics.

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
