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

Canonical typed and ternary file inputs use an opened regular descriptor with
a strict nonzero 1 MiB limit. The publisher admits descriptor/path metadata
before and after its bounded read, rejecting observed inode replacement or
same-sized in-place rewrites even if the original byte count still matches.
On POSIX the admission compares device/inode and nanosecond modification and
change stamps; Windows uses available file identity and write/change stamps.
A stable symlink to a regular source remains valid. On Linux the reader
also resolves the initial canonical wire path and checks the actual opened
file pathname through `/proc/self/fd` before and after the bounded read. This
rejects parent-directory symlink redirection to an outside hard link of the
same original inode during an injected read, even when every timestamp, byte
and inode check remains equal. Unavailable descriptor-path evidence rejects;
other platforms retain their metadata-based contract. These checks reject
observed concurrent drift, not changes after the final admission check or
atomic source snapshots against a racing writer.

The publisher creates a new same-directory staging file, flushes/syncs and
rereads its exact graphical bytes through the original read/write descriptor,
with an allocation budget of the expected source length plus one byte. It
independently rechecks the synced descriptor's size, timestamps and identity
against the nonfollowing staging pathname both before and after the bounded
reread; the published hard link must still name the original staged inode.
A pathname replaced with an equal-byte file or symlink cannot be certified,
and cleanup only removes a still-matching original stage, preserving foreign
substitutions. The publisher also requires exactly one hard link to the opened
staging inode before publication and exactly two (staging and final target)
while verifying the newly published target. An extra hard link before the first
link blocks target creation; an extra alias observed after publication rejects
success while retaining the already-visible target. On Unix the link count is
read from inode metadata; on Windows it uses the native optional link count and
fails closed if that evidence is unavailable. Independent injected-alias tests
cover both stages and retain any unrelated hard-link pathname. The stage's
original resolved pathname is also pinned before publication and rechecked
before and after both bounded rereads. Renaming a parent and installing a
symlink back to the *same inode* changes that resolved pathname, so it rejects
before publication or before declaring an already-published target successful.
Stable parent symlinks present at initial opening remain permitted. The final
inode and path checks detect observed substitutions but do not establish an
atomic filesystem snapshot against ongoing writers.
The no-overwrite hard link atomically reveals the final `.malbolge` only after
staged content admission. Existing targets and
symlinks are never replaced; invalid profiles, operands, paths or layout
shapes fail closed. Process-level integration tests execute the built binary,
reopen emitted files under historical/current canonical profiles with real
byte input, test forward jumps and relocated arithmetic, compare exact output
bytes across independent runs, reject unsupported input and symlinks, and
exercise concurrent writers to one target. A separate three-jump external
process fixture publishes both raw and capsule sources under both profiles,
reopens and executes the exact outputs, and rejects a forged later destination
without creating a final file. On abrupt interruption a hidden
staging file may remain; it cannot expose a partial final target. A later
producer preserves any occupied `.stage-<pid>` staging pathname and retries
fresh sequence-suffixed names via exclusive creation, with 32 total attempts.
For output filenames whose full staging suffix would exceed a conservative
128-byte basename budget, the publisher uses a compact, reproducible
64-bit FNV-1a digest of the complete UTF-8 target filename instead of embedding
the original name in the stage. The digest is only a collision-prone name hint:
exclusive creation and bounded retries still prevent overwriting any existing
stage, including a digest collision. Distinct valid long output filenames
publish independently without overflowing a common 255-byte filesystem
component limit. An occupied hashed staging name is preserved and retried.
Only its own newly created stage is removed; exhausted collisions reject
before touching the verified source or an existing target.

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

### Canonical input-file nonblocking descriptor admission

`--typed-file` and `--ternary-file` share one bounded regular-file reader.
On Linux/Android it calls a safe Rust `OpenOptionsExt` reader with the
platform's `O_NONBLOCK` status bit, and admits the *opened descriptor*
only if it is a nonempty regular file no larger than 1 MiB. Consequently
stable FIFOs and writerless FIFOs substituted for a regular path immediately
before open cannot stall; a regular-file symlink remains permitted. The
handle's exact bounded bytes are canonical-admitted separately, irrespective
of how its path name was changed concurrently. On other platforms, a
resolved-path metadata check still precedes ordinary open, followed by the
same descriptor check; it cannot guarantee no blocking under pathname swaps.

Watchdog-protected subprocess tests verify immediate refusal for raw and
symlinked writerless FIFOs in MCTI/MCTR modes; a regular linked typed file
still executes under the VM. A Linux stress regression atomically alternates
a candidate symlink between a corrupt regular file and a writerless FIFO
while 32 separate publisher instances check both modes. Every instance
rejects before output and finishes without blocking. The stress test does
not exhaustively force every possible race interleaving, nor does the
publisher authenticate that an input retained the same pathname throughout
validation. Independent canonical-byte checks and atomic no-clobber final
publication remain distinct guarantees.

### Genuine Nonzero Byte Constant Artifact Pilot

The explicit `--seeded-byte-literal` mode admits one verified nonzero
`u8` literal and one to nine matching outputs via canonical MCTI
or MCTR file/stdin. The original 14-value current-profile seed table
remains exclusive to single-output sources. Ten different byte values
`55, 64, 65, 66, 163, 164, 165, 182, 183, 200` have a separately
verified two-output seed table. Third- through ninth-output phases add
21, 24, 18, 19, 18, 21 and 21
independently re-executed distinct byte values, respectively. Each additional
`<` changes source position decoding and loader-expanded guest memory,
so reusing an older single-output seed could
print the wrong byte. Both the linear layout admission and independent
normative VM must prove safe
code/data separation, exact repeated-byte outputs and zero consumed input.
Raw and version-one capsule publication retains the existing atomic
no-overwrite semantics. General-runner process tests select the current
profile through a capsule; raw graphical source carries no profile ID and
can produce different values under the runner's historical default.
The guest computes the byte without a host-provided result. Other profiles,
unknown literals, zero/ten-or-more outputs, additional effects and arbitrary
arithmetic reject.

### Signed/unsigned byte identity-cast artifact publication

A distinct `--identity-byte-trace` canonical MCTI/MCTR file/stdin mode
verifies exact eight-bit `IntegerBitcast` SSA aliases of the most recent
successful input, preserving source spans and identity while emitting no
opcode for the casts themselves. The independently checked bridge emits
real input, output and halt instructions only; all old aliases invalidate
at each later read. The publisher recomputes exact successful-byte
output and consumption under two normative VM patterns, with the same
4096-code-cell bound, independent layout/profile check and atomic
no-clobber raw/capsule framing. Legacy echo, latest-read, initial-zero
and zero-prefixed modes reject casts without the explicit opt-in.

This realizes no host guest computation, byte-register storage, EOF/error
handling, branch flow, arbitrary C lowering or callable guest ABI.

### Zero-prefixed successful-byte artifact publication

The distinct `--zero-prefixed-byte-trace` mode accepts canonical MCTI or
MCTR file/stdin only when it contains an independently validated zero
constant SSA, one or more leading same-SSA byte outputs, followed by real
byte inputs and outputs of only the most recent input SSA. The initial
zero comes from the real VM accumulator, not host evaluation. The target
contains actual Malbolge output/input/halt cells, with the same 4096-cell
maximum. A post-read output of the original zero SSA is explicitly
rejected as unsound without guest memory. The canonical typed adapter
reconstructs exact MCTR provenance; the separate publisher re-decodes and
re-encodes the ternary target before any artifact write. Two distinct
successful-byte VM patterns confirm literal zero prefix, latest-read
output order, exact input consumption and termination. The existing
atomic no-clobber raw/capsule publisher is unchanged. The opt-in prefix
cannot mix with any other canonical mode or machine-op tokens.

Real MCTI/MCTR split-wire tests require the target path to remain absent
while a producer holds the stream open, both with partial and complete
canonical bytes. Publication occurs only after actual EOF and complete
independent admission.

This is not arbitrary constant lowering, I/O EOF handling, callable guest
ABI, or general dataflow/control-flow code generation.

### Initial-zero typed and ternary source publication

An explicit `--initial-zero-output` prefix for `--typed-file`,
`--ternary-file`, `--typed-stdin` and `--ternary-stdin` enables the
independently admitted `MaterializeU8(0)` plus one or more same-SSA guest
byte outputs and void return. The VM starts with accumulator zero; the
verified graphical code executes only actual output operations and halt.
No source operation is executed by host software. MCTI first undergoes
full canonical module admission, typed-source projection, canonical MCTR
re-encoding and independent re-decoding. Both wire kinds are then checked
by the same independent zero-output bridge, real VM empty/extra-input
termination and exact guest-output oracle, and the existing atomic raw or
capsule no-overwrite publisher. This differs deliberately from successful
byte-input preflight: zero output consumes no input and rejects any extra
source effects. The CLI grammar makes this flag mutually exclusive with
`--latest-byte-trace`, leaving default strict echo unchanged. An external
MCTI/MCTR zero-output stream test checks that partial and completely written
canonical wires remain unpublished until their producer supplies EOF; after
closing the pipe the exact independently verified source is published.

Only a bounded initial-zero constant is implemented: no general nonzero
constant materialization, guest C ABI, libc, dataflow, EOF or C compilation.

### Canonical wire streaming publication

The verified file emitter now has explicit `--typed-stdin` (MCTI) and
`--ternary-stdin` (MCTR) source modes, with optional preceding
`--latest-byte-trace`. Each takes zero path operands and reads up to
1,048,577 bytes through standard input, rejecting empty wires and byte
counts above 1 MiB before parsing or publishing. The input producer must
close the stream to supply EOF. Neither regular-file mode accepts FIFOs;
streaming is deliberately opt-in so callers cannot accidentally block on a
path that merely looks file-like.

Both streams rejoin the *existing* canonical module/ternary decoder,
profile admission, independently re-encoded position-sensitive source,
normative VM execution and two deterministic successful-byte input checks.
Raw and capsule outputs reuse the original staged no-overwrite publisher.
External process regressions compare stdin and regular-file output bytes,
reopen capsules, execute the generated source under the real normative VM,
and reject empty, oversized, malformed, wrong-kind and trailing-option
inputs without final artifacts or overwrites. This is a bounded producer
interface, not a generic guest runtime, C compiler or unbounded stream
transformer; it does not implement EOF I/O semantics inside the guest.
An additional fragmented-input process fixture feeds a partial canonical
MCTI header, verifies no output path exists while the producer keeps the
pipe open, supplies the rest in single-byte writes, then closes the pipe.
Only after EOF does the publisher create target bytes independently equal
to typed-module lowering. This demonstrates complete-source publication,
not partial stream execution.

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

The typed-file publisher remains bound to the original canonical MCTI-v1
`malbolge-2026` profile, unlike the lower-level layout library which admits
five registered VM identities. Selected historical/immutable profiles
fail before source lowering and publication, rather than silently replacing
the typed source's profile. Current-profile strict/latest-read capsules
are independently reopened and executed by the normative VM and real
binary-stdin runner. A physical source-capacity regression publishes an
exactly 4096-cell MCTI trace and verifies all 4094 identical byte outputs;
adding a single output cell fails without a final file.

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
