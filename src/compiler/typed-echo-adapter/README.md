# Typed Echo Adapter

## Purpose

Close executable typed-IR-to-ternary byte-I/O compiler gaps without relying
on a caller-manufactured semantic projection. The entrypoint accepts canonical
`malbolge-typed-ir-v1` bytes, verifies exact syntax and admitted typed IR,
projects the complete source function/effect trace, and lowers to canonical
`malbolge-ternary-ir-v1` (`MCTR`) bytes. It then separately decodes those
bytes, compares complete stage state, and passes the admitted result through
the existing independently verified Malbolge byte-echo layout backend.

## Effect-free void return

`compile_canonical_typed_empty_void` admits one canonical no-parameter,
no-effect, one-block void function. It preserves exact typed source identity,
lowers the return to independently re-decoded MCTR, and encodes an executable
`NoOperation` / `Halt` guest source through the verified layout bridge.
Nonempty instructions, globals, proof obligations, foreign profiles and
non-void returns reject. A real VM and CLI capsule regression proves two
steps with no output or consumed input, including after supplied input bytes.
This is not yet a C source frontend driver or general return-value ABI.


All opt-in modes accept exactly one no-argument, non-variadic, void-return
function;
one entry block without phi nodes; and no globals or proof obligations.
`compile_canonical_typed_echo` preserves the original strict contract: one
or more adjacent successful typed-`u8` `ByteInput`/`ByteOutput` pairs using
the identical SSA ID. At most 2047 pairs fit its 4095-cell direct source.

`compile_canonical_typed_latest_byte_trace` is an explicit opt-in superset:
one or more successful byte inputs with zero or more outputs, each using
**only the most recent input's** exact SSA ID. A byte may be replayed many
times or consumed without output. A later read overwrites the VM accumulator;
replaying an older (but still valid typed-IR) SSA byte would require guest
memory and is rejected. The maximum verified layout has 4096 code
cells. Function, source
ID/digest, ABI, profile, return and operation spans all originate from the
validated upstream module. Unsupported shapes reject before any source
emission. This bridge does not perform I/O on the host.

A third, separately opt-in entrypoint,
`compile_canonical_typed_initial_zero_outputs`, accepts exactly one `u8`
`ConstantInteger(0)` SSA definition followed by one or more `ByteOutput`
instructions referring to that same SSA ID. It projects the real typed source
spans and exact constant bits into canonical MCTR, re-decodes that wire and
calls the independently verified `encode_initial_zero_outputs` target bridge.
The normative VM initializes its accumulator to zero, so every emitted
`OutputByte` executes on the guest without consuming any input. The target
contains only `OutputByte` instructions and a final `Halt`, while the
source-constant's provenance remains in the ternary IR. A maximum of 4095
outputs fits the 4096-cell code bound. Nonzero or additional constants,
other instructions, stale SSA, profile drift, and empty output traces reject.
Neither the original adjacent-echo API nor latest-read API is broadened.

A fourth opt-in `compile_canonical_typed_zero_prefixed_latest_byte_trace`
composes **initial zero outputs followed by the latest successful input**
without any host guest-byte emulation. It accepts exactly one canonical
`u8 ConstantInteger(0)` SSA definition, one or more outputs of that exact
zero SSA before the first `ByteInput`, one or more successful byte inputs,
and at least one output of the most recent input's SSA. Later reads
replace the accumulator; no zero SSA or older input SSA can be replayed
then. It admits exactly one void, no-argument function and one block,
retaining every instruction/source span and source/ABI/target identity
through independent canonical MCTR re-decoding and target layout.
All I/O operations run inside the selected normative VM; successful I/O
and unobserved return/ABI remain the declared limits. Maximum source is
4096 code cells, excluding the zero materialization already proven by
initial A=0. Nonzero/extra scalar definitions and unsupported operations
fail closed; all earlier adapter modes retain their original domains.

For input-based modes the equivalence claim requires successful byte
reads and writes with an ignored void ABI. Initial-zero output consumes no
input, but its guest writes must still succeed. None of the four modes
implements EOF, failed I/O, arithmetic, control flow or C source parsing.
The typed source digest remains copied provenance, not authentication of
external files.

### Canonical signed/unsigned byte-bitcast trace

The fifth byte-trace adapter mode
`compile_canonical_typed_identity_byte_trace` accepts exactly one
no-argument void-return canonical MCTI function with one phi-free block.
It admits `ByteInput`, `ByteOutput` and exact eight-bit `IntegerBitcast`
instructions between canonical `i8` and `u8`. Only aliases of the latest
successful input remain executable in the machine accumulator. The
source/SSA spans, source digest, ABI and profile identity survive ternary
lowering, canonical MCTR re-admission and independent target encoding.

The explicit CLI mode `--identity-byte-trace` accepts bounded MCTI/MCTR
through `--typed-file`, `--ternary-file`, `--typed-stdin`, or
`--ternary-stdin`. It proves exact byte I/O under two normative VM input
patterns, compares the independently re-encoded typed and ternary sources,
and uses existing atomic raw/capsule no-clobber publication. In particular,
a signed-byte alias is *not* a successful `u8` output until it has been
bitcast back; old zero-only, adjacent-echo and latest-read modes do not
admit casts. No host callback, EOF, arithmetic, byte register file,
branching or guest return ABI is implemented by this slice.

### Canonical one- to thirty-three-output nonzero literal

The separate `compile_canonical_typed_rotated_byte_literal` accepts a
canonical MCTI `u8 ConstantInteger`, one to thirty-three same-SSA `ByteOutput`s,
and `ReturnVoid` in a single no-argument void function. It preserves
source, SSA, ABI, profile and span identity through canonical MCTR and a
verified position-sensitive graphical source. The guest computes its `u8`
through genuine `j` data relocation and `*` rotation, not a host callback.
Fourteen current-profile nonzero values have one-output witnesses; ten
*different* values have exact two-output witnesses; 21 values have
independently witnessed three-output layouts. A fourth-output table realizes
24 distinct bytes from 26 short real-VM source phases. A fifth-output
scan of the same 26 bounded phases witnesses 18 distinct nonzero bytes and
retains their shortest valid prefixes. Sixth- and seventh-output short
scans produce 19 and 18 distinct byte witnesses from 26 real VM phases
apiece. Eight outputs produce 21 distinct bytes from 26 independently
replayed source phases. Nine outputs also yield 21 distinct bytes from
26 independent phases. Ten outputs yield 25 distinct bytes across the
same 26 tested phases. Eleven outputs yield 17 distinct values across
26 independently replayed phases. Twelve outputs yield 20 distinct values
from the same independently replayed 26 phases. Thirteen outputs yield 19
distinct bytes from another 26 independently re-executed phases. Fourteen
outputs yield 22 distinct bytes from 26 independently verified phases.
Fifteen outputs yield 17 distinct bytes from 25 admissible phases in the
26-phase scan; phase 20 is excluded. Sixteen outputs realize 24
nonzero bytes from 26 verified phases; seventeen outputs realize 19
distinct bytes from another 26 separately VM-executed phases. Eighteen
outputs realize 20 distinct nonzero bytes across all 26 independently
VM-checked phases, including duplicated byte values. Nineteen outputs
realize 19 distinct bytes across 26 separate VM phases. Twenty outputs
realize 21 distinct nonzero bytes in 26 independently replayed phases.
Twenty-one outputs yield 20 distinct bytes from 25 successful phases;
phase fourteen does not qualify. Twenty-two outputs yield 25 distinct
nonzero bytes from all 26 verified phases, retaining the shorter of two
witnesses for byte 200. Twenty-three outputs realize 21 distinct
nonzero values across all 26 successful phases, retaining the earliest
source prefix for repeated bytes. Twenty-four outputs admit 25 of 26
real-VM phases (not phase seven), retaining 21 distinct shortest prefixes.
Twenty-five outputs admit 25 phases (again excluding phase seven),
retaining 19 distinct shortest byte witnesses from real VM output.
Canonical typed and capsule/runner fixtures verify byte values 18 and 44.
Twenty-six outputs succeed for 24 bounded phases (excluding six and
seven), retaining 22 shortest byte witnesses; canonical and real-runner
fixtures prove byte values 196 and 137. Twenty-seven outputs
admit 23 of 26 VM phases (not six, seven or eight), retaining 18 distinct
shortest nonzero byte witnesses. Canonical typed and capsule/real-runner
fixtures verify 138 and 41. Twenty-eight outputs independently pass
23 phases (excluding five, six and seven), retaining 22 shortest
nonzero byte witnesses; canonical/capsule runner fixtures prove 63 and 19.
Twenty-nine outputs pass 23 independent phases (excluding five,
six and seven), retaining 19 distinct shortest byte witnesses;
canonical/real-runner fixtures verify 12 and 25. Thirty outputs admit
22 independently checked phases (not four through seven), retaining
20 distinct shortest bytes; canonical/real-runner fixtures verify 55 and 150.
Thirty-one outputs admit 22 independent phases (not four through seven)
with 19 distinct shortest byte witnesses; typed/real runner verifies 22 and 160.
Thirty-two outputs admit 21 independent phases (not three through seven)
with 20 distinct shortest byte witnesses; typed/real runner proves 200 and 15.
Thirty-three outputs pass 21 short VM phases (not three through seven)
with 18 distinct shortest byte witnesses; typed/real runner proves 136 and 158.
Thirty-four or more outputs reject.
Each count admits only its shortest verified prefix per byte.

### Distinct zero-then-printable byte pair

The independent `compile_canonical_typed_zero_then_literal` mode accepts exactly
four source-bound operations: `u8` constant zero, output of that SSA, a second
new `u8` constant `Z`/`P`/`T`/`S`, and output of its own distinct SSA, with
one final void return. It preserves both definitions, source spans and order
through canonical typed IR and MCTR re-admission. The current-profile guest
actually emits the first zero from initial accumulator, then executes
`j`/`p` to calculate the second byte. Exact padding phases 0/2/6/17 yield
5/7/11/22 VM steps. The target bridge and publisher independently run the
normative VM with empty and irrelevant nonempty input to verify the two-byte
output before publication. Reverse order, unsupported values, stale SSA,
extra effects and other profiles reject; this is not general mixed-literal
synthesis.

Each added `<` changes the full loader-expanded memory, so seeds cannot be
reused across output counts.
Each candidate is re-executed before admission. Other values and output
counts reject.
The opt-in CLI `--seeded-byte-literal` supports MCTI/MCTR file or bounded
stdin with raw/capsule no-clobber publication. EOF, general arithmetic,
arbitrary output sequences and guest ABI remain unimplemented.

## Validation

```sh
cargo test --locked --test typed_echo_adapter --quiet
cargo clippy --locked --test typed_echo_adapter -- -D warnings
```

The integration suite checks independently restored typed/MCTR state and
real `ProfileMachine` output across multiple trace sizes. It also covers
the all-byte domain, exact 4096-cell upper bound, stale SSA rejection and
byte-identical old/new output for ordinary echo traces.

The `malbolge_layout` publisher now accepts canonical typed modules directly:

```sh
cargo run --bin malbolge_layout -- \
  --profile malbolge-2026 --output .temp/typed-echo.malbolge \
  --capsule -- --typed-file .temp/typed-echo.mcti
```

`--typed-file` defaults to strict adjacent echo. For latest-read traces use
`--latest-byte-trace --typed-file .temp/latest-read.mcti`. Both direct paths
internally re-decode the adapter's canonical MCTR output and re-encode its
position-sensitive Malbolge source with the *independent ternary bridge*,
requiring byte-identical source, exact profile fingerprint and code witness
length. The same normative VM successful-byte patterns and raw/capsule
no-clobber publication are retained. The integration regressions compare
both direct paths byte-for-byte against the older explicit MCTR workflow and
reject malformed, wrong-profile, stale-SSA and oversized MCTI without
creating a target. A direct MCTI-to-capsule-to-real-general-CLI regression
additionally feeds three binary guest bytes (including 0 and 255) and
requires the expected repeated latest-byte output; grammar errors and
trailing mixed-mode operands fail closed.

For the initial-zero-only subset, use the separate
`--initial-zero-output --typed-file PATH` or
`--initial-zero-output --ternary-file PATH` forms. The same options also
accept `--typed-stdin` and `--ternary-stdin` for a bounded canonical wire
producer. Each source enters the existing independently re-decoded MCTR,
position-sensitive target verification, exact no-input/extra-input normative
VM output-and-consumption preflight and no-overwrite raw/capsule publisher.
The explicit mode is incompatible with `--latest-byte-trace`; the default
commands remain strict adjacent byte echo. A real-process fragmented-wire
test verifies neither MCTI nor MCTR zero-output stdin may publish before
EOF, even after receiving the complete canonical byte sequence. Canonical
source files and pipes are compiler inputs, not guest stdin. This still
does not implement C input, nonzero output or a callable C guest ABI.

For mixed initial-zero/latest-byte traces, use the independent opt-in
`--zero-prefixed-byte-trace --typed-file PATH` or
`--zero-prefixed-byte-trace --ternary-file PATH` CLI input. Their
`--typed-stdin` and `--ternary-stdin` analogues accept bounded canonical
wire streams; both
rejoin the independently admitted MCTR and normative VM preflight.
The publisher checks two fixed full-byte input patterns and expects leading
literal zero outputs, then outputs of only the latest successful read,
matching output and consumed-input count exactly. A source that reuses the
initial constant after a read cannot publish. Raw/capsule framing and atomic
no-clobber semantics are shared; the flag cannot mix with other modes.
A real split-wire regression checks that neither MCTI nor MCTR can publish
before EOF, even after its producer has sent the complete canonical bytes.

Canonical MCTI wire version one is intentionally pinned to `malbolge-2026`
and `malbolge-c32-v1`: unlike the lower-level VM and standalone layout
encoder, this typed compiler stage does **not** admit historical or immutable
versioned profile identities. The adapter now rejects a selected-profile
drift immediately after full canonical typed admission, before source
effect projection or ternary lowering. A real file-publisher regression
checks both strict and latest-read current-profile capsules through the
normative VM and actual binary-stdin runner, and rejects all four other
registered profile selectors without publishing. Another regression
publishes the entire 4096-cell latest-read trace (one read, 4094 outputs),
checks exact `0xff` guest output and consumption, and refuses 4097 cells.
This does not generalize the typed ABI or imply EOF semantics.

For the original strict echo subset, canonical `MCTR` bytes remain consumable
by the default `malbolge_layout --ternary-file` CLI. Its separate opt-in
`--latest-byte-trace --ternary-file` path now accepts the latest-successful-read
subset, preserving the same real VM preflight and no-clobber raw/capsule
publisher. The typed-adapter test exercises full canonical MCTI-to-MCTR-to-
published-capsule provenance, reloading the independent normative VM and
checking repeated output and unused consumed input. The strict default still
rejects this nonadjacent trace. Neither path realizes EOF, failed I/O, guest
byte storage, arbitrary C operations, source authentication or guest ABI.

The distinct-nonzero-literal-pair mode preserves two separate source-bound
`u8` SSA constants and their output references. Only `Y/`, `Y$`, and `Q.`
produce a fully independently decoded and guest-verified artifact. Other
constant pairs and additional effects remain unsupported.

### Three independently verified literal outputs

`compile_canonical_typed_distinct_literal_triple` admits only source-proven
`Z%H`, `Q.O`, `Y-P`, `T"O`, and `T"Q` under the current profile,
preserving three different
`u8` constant SSA definitions, each output use and exact source spans. The
canonical MCTI/MCTR round trip feeds the separate triple bridge; the
real VM independently verifies all three writes and exact termination.
All other triples, stale SSA, foreign profiles and extra effects reject.

### Four-distinct-byte current-profile witness

The separately selected `T=4>` literal-output mode preserves four distinct
source-bound `u8` constant definitions and four exact SSA byte outputs. Its
independently verified positional target uses eleven no-ops, one data-pointer
relocation and four separate guest `CrazyData`/output pairs before halt. The
normative current-profile VM emits `T=4>` in exactly 21 steps with no input
consumption. Partial prefixes, other four-byte values, stale SSA identities,
foreign profiles and unproved arithmetic remain unsupported; this is not a
general C string-output implementation.

### Five distinct guest-computed bytes (bounded binary witness)

The opt-in `--distinct-literal-quint` mode admits five source-proven byte
constants only for `51 22 1b 37 39` (hex: `Q`, quote, ESC, `7`, `9`).
The eleven-nop relocated target performs five disjoint guest `CrazyData`
writes and executes five actual byte outputs in 23 normative VM steps.
Canonical typed/MCTR identity, all five SSA bindings, profile, input-free
execution, and the raw/capsule publisher are independently rechecked.
Incomplete prefixes, different five-byte outputs, and additional effects
fail without output; this witness is not general C string compilation.

### Six distinct guest-computed bytes (bounded binary witness)

The opt-in `--distinct-literal-six` path admits the exact current-profile
source byte trace `51 1c 4f 1d 50 1b` (hex). Six independent source-bound
`u8` SSA definitions and output uses survive canonical typed/MCTR admission.
A single inert prefix and data-pointer relocation precede six guest
`CrazyData` writes and six byte outputs, all outside the source region.
The normative VM independently emits all six binary bytes in 15 steps with
no consumed input. Both raw and capsule publishers recheck this witness;
unsupported values, partial prefixes, extra output, or stale SSA fail closed.
This does not implement general C string output or the guest C runtime.

### Seven distinct guest-computed bytes (bounded binary witness)

The opt-in `--distinct-literal-seven` path admits only the independently
verified current-profile C output trace `36 3e 35 02 54 1f 18` (hex). Seven
source-bound `u8` SSA definitions survive canonical typed/MCTR admission.
Five inert no-ops and one data-pointer relocation precede seven separate
guest `CrazyData` writes and outputs, with data cells outside the source.
Both raw and capsule publication require normative VM output of these exact
seven bytes in 21 steps, independent of unused input. Incorrect prefixes,
reordered bytes, extra output and altered SSA are rejected without publication.
This remains a finite witness, not general C byte-string lowering.

### Eight distinct guest-computed bytes (bounded mixed arithmetic witness)

The opt-in `--distinct-literal-eight` C path admits exactly eight separate
source `putchar` constants with the independently verified current-profile
binary stdout `53 20 17 3c 36 01 52 06` (hex): `S`, space, ETB, `<`, `6`,
SOH, `R`, ACK. Three no-ops and one data-pointer relocation precede seven
real guest `CrazyData` writes and a final `RotateData` write, each followed by
guest output, then halt. The normative VM proves all eight distinct bytes in
21 steps with disjoint post-source data writes, independent of unused input.
Incomplete prefixes, reordered bytes, duplicate SSA and foreign profiles
reject without publishing an output. This is one finite source witness, not
arbitrary binary C output or general lowering.

### Nine distinct guest-computed bytes (bounded mixed arithmetic witness)

The opt-in `--distinct-literal-nine` C path admits exactly nine separate
source `putchar` constants with proven current-profile binary output
`54 3d 8d d1 c0 b4 bf d2 a2` (hex). One reached no-op and explicit
relocation precede eight real guest `CrazyData` writes and one `RotateData`
write (the third arithmetic step); each data write is followed by output.
The normative VM verifies nine distinct bytes, 21 total steps, nine disjoint
post-source data writes and zero consumed input before publication. Incomplete
prefixes, reordered bytes, altered SSA, foreign profiles and extra writes
reject; this is a finite source witness, not generic byte-string lowering.

### Ten distinct guest-computed bytes (bounded mixed arithmetic witness)

The opt-in `--distinct-literal-ten` C path admits exactly ten separate
source `putchar` constants with proven current-profile binary output
`51 22 fd ce a5 98 ba b6 87 cb` (hex). One reached no-op and explicit
relocation precede nine real guest `CrazyData` writes and one `RotateData`
write (the third arithmetic step); each data write is followed by output.
The normative VM verifies ten distinct bytes, 23 total steps, ten disjoint
post-source data writes and zero consumed input before publication. Incomplete
prefixes, reordered bytes, altered SSA, foreign profiles and extra writes
reject; this is a finite source witness, not generic byte-string lowering.

The eleven-byte C witness is separately admitted as an exact source-bound
`P`, GS, SUB, `6`, ENQ and six binary values. Eleven guest writes
produce 11 distinct bytes in 24 VM steps; the normative VM verifies
raw and capsule outputs without host computation substitution. This
finite trace is not general C byte-stream lowering.

The `--distinct-literal-twelve` C path admits the exact twelve-byte
`51 37 34 38 fb ce 9f 98 b8 b4 83 cd` witness. One reached no-op,
explicit relocation, eleven disjoint `CrazyData` writes and one
`RotateData` write at the fifth arithmetic position emit twelve guest
bytes in 27 VM steps. The normative VM independently verifies both
source-bound outputs and input independence before publication. Other
byte sequences, incomplete prefixes, and forged SSA are not admitted;
this is not general binary-stream lowering.

The `--distinct-literal-thirteen` C path admits only the exact thirteen
source-ordered bytes `42 43 30 16 54 09 bf c6 c8 87 e3 ab a4` (hex).
One reached no-op and a data-pointer relocation precede twelve disjoint
guest `CrazyData` writes and one `RotateData` write (the sixth arithmetic
position), each followed by guest output. The normative current-profile VM
replays the thirteen binary bytes in 29 steps with no consumed input before
raw or capsule publication. Any incomplete, reordered or forged effect trace
rejects; this finite witness does not provide general C byte-stream lowering.


The `--distinct-literal-fourteen` C path admits only the exact fourteen
source-ordered bytes `59 45 2c 48 53 17 4c 4f 3d 40 5b 31 19 34` (hex).
One reached no-op and a data-pointer relocation precede twelve disjoint
guest `CrazyData` writes and two `RotateData` writes (the sixth and thirteenth
arithmetic positions), each followed by guest output. The normative current-profile VM
replays the fourteen binary bytes in 31 steps with no consumed input before
raw or capsule publication. Any incomplete, reordered or forged effect trace
rejects; this finite witness does not provide general C byte-stream lowering.


The `--distinct-literal-fifteen` C path admits only the exact fifteen
source-ordered bytes `51 2e 19 38 3e 89 d2 ad a3 b7 c8 88 08 d5 c6` (hex).
One reached no-op and a data-pointer relocation precede thirteen disjoint
guest `CrazyData` writes and two `RotateData` writes (the sixth and thirteenth
arithmetic positions), each followed by guest output. The normative
current-profile VM replays fifteen binary bytes in 33 steps with no consumed
input before
raw or capsule publication. Any incomplete, reordered or forged effect trace
rejects; this finite witness does not provide general C byte-stream lowering.

The `--distinct-literal-sixteen` C path admits only the exact sixteen
source-ordered bytes `3f 49 36 13 5a 0a ba b3 c3 86 cc aa 01 07 d5 c5` (hex).
One reached no-op and a data-pointer relocation precede thirteen disjoint
guest `CrazyData` writes and three `RotateData` writes (the sixth,
thirteenth and fourteenth arithmetic positions), each followed by guest
output. The normative current-profile VM replays sixteen binary bytes
in 35 steps with no consumed input before raw or capsule publication.
Incomplete, reordered or forged effect traces reject; this finite
witness is not general C byte-stream lowering.

The `--distinct-literal-seventeen` C path admits only the exact seventeen
source-ordered bytes `59 3f 2c 48 50 1b 18 32 15 4d 4b 3b 42 0f 44 30 17` (hex).
One reached no-op and a data-pointer relocation precede fourteen disjoint
guest `CrazyData` writes and three `RotateData` writes (the seventh, ninth
and fourteenth arithmetic positions), each followed by guest output.
The normative current-profile VM replays seventeen binary bytes in
37 steps with no consumed input before raw or capsule publication.
Incomplete, reordered or forged effect traces reject; this finite
witness is not general C byte-stream lowering.

The `--distinct-literal-eighteen` C path admits only the exact eighteen
source-ordered bytes
`54 22 19 3e 38 03 09 dd 87 d1 a5 99 bf 08 c7 c6 c2 91` (hex).
One reached no-op and a data-pointer relocation precede fifteen disjoint
guest `CrazyData` writes and three `RotateData` writes (the seventh, ninth
and fourteenth arithmetic positions), each followed by guest output.
The normative current-profile VM replays eighteen binary bytes in
39 steps with no consumed input before raw or capsule publication.
Incomplete, reordered or forged effect traces reject; this finite
witness is not general C byte-stream lowering.

The `--distinct-literal-nineteen` C path admits only the exact nineteen
source-ordered bytes
`53 21 1a 3c 38 03 17 55 0e 49 2b 10 46 16 40 4c 3a 19 58` (hex).
A first-instruction data-pointer relocation precedes sixteen disjoint
guest `CrazyData` writes and three `RotateData` writes (the seventh, ninth
and fourteenth arithmetic positions), each followed by guest output.
The normative current-profile VM replays nineteen binary bytes in
40 steps with no consumed input before raw or capsule publication.
Incomplete, reordered or forged effect traces reject; this finite
witness is not general C byte-stream lowering.

The `--distinct-literal-twenty` C path admits only the exact twenty
source-ordered bytes
`3e 14 35 12 3f 0a a4 9c ad a3 1a a8 a2 95 ab 9f 98 1d ac ae` (hex).
Twelve reached no-ops shift `j` to position twelve, relocating the data
pointer beyond the 54-cell source. Seventeen guest `CrazyData` writes and
three `RotateData` writes (the seventh, eleventh and eighteenth arithmetic
positions) compute distinct bytes on disjoint guest cells, followed by output.
The normative current-profile VM replays all twenty bytes in 54 steps with
no input consumed before raw or capsule publication. Incomplete, reordered
or forged effects reject; this remains a bounded C lowering witness.

The `--distinct-literal-twenty-one` C mode admits only the exact
twenty-one source bytes
`41 0e 3b 0f 3f 0a 40 8e 26 92 27 96 22 97 8d 15 31 18 35 1a 2f` (hex).
Fifteen no-ops relocate the data pointer at position 15. Eighteen
`CrazyData` and three `RotateData` writes (the eighth, fifteenth and
sixteenth arithmetic positions), plus one reached trailing no-op,
produce twenty-one distinct guest bytes in 60 real VM steps.
The exact C effects are verified without host-side output replacement;
unproved prefixes, reordered literals and forged artifacts reject.

The `--distinct-literal-twenty-two` C path admits exactly the twenty-two
source-ordered bytes `39 16 37 05 41 0c 30 8e 24 9f 1b a0 23 97 15 28
27 29 14 32 1e 1f` (hex). Ten no-ops move the relocating `j` to source
position ten; twenty `CrazyData` and two `RotateData` writes compute the
bytes outside the 57-cell source, with a reached no-op before halt. The real
VM independently verifies all 22 output bytes, zero consumed input and exact
57-step termination before raw or capsule publication. Arbitrary
twenty-two-byte source sequences remain unsupported.

The canonical typed-IR `--distinct-literal-twenty-three` mode preserves
23 source-bound `u8` constants and 23 matching `ByteOutput` SSA uses, then
requires an independent real-VM layout proof before publication.

The canonical typed-IR `--distinct-literal-twenty-four` path preserves
24 exact `u8` definitions and their matching `ByteOutput` SSA uses; its
physical guest layout must pass independent real-VM verification.

The canonical typed-IR `--distinct-literal-twenty-five` path preserves
25 exact `u8` definitions and the matching 25 `ByteOutput` SSA uses.
Only the independently proved 25-byte source trace reaches the real VM.

The `--distinct-literal-twenty-six` typed-IR mode admits precisely 26
source-bound `u8` constant definitions and matching `ByteOutput` SSA uses.
Independent guest verification remains mandatory before publication.

The `--distinct-literal-twenty-seven` typed-IR route preserves 27 separate
source-bound `u8` constants, matching `ByteOutput` SSA values and a void
return. Independent ternary admission and real-VM verification remain required.

The `--distinct-literal-twenty-eight` typed bridge now admits the exact
28 verified byte-constant/output SSA pairs, projects through canonical
ternary IR and rejects altered values, SSA identity and profile drift.

The `--distinct-literal-twenty-nine` typed bridge admits exactly 29 source-
bound `u8` constants and matching `ByteOutput` SSA uses. Canonical ternary
re-admission and real-VM execution prove the resulting guest output; altered
values, SSA identity or target profile refuse before publication.

The `--distinct-literal-thirty` typed bridge preserves 30 source-bound
`u8` materializations with matching byte-output SSA uses and void return.
It independently re-admits canonical ternary IR and verifies all 30 bytes
against the 97-step real VM. Foreign profiles and altered effects reject.

The separate `--distinct-literal-thirty-one` typed mode binds 31 distinct
`u8` constants and their exact SSA uses to independently checked ternary
effects. Only the finite VM-proven sequence is admitted; wrong profiles,
lengths, SSA and values reject before guest publication.

The `--distinct-literal-thirty-two` typed bridge independently admits the
32 exact `u8` constants, matching byte-output SSA uses and void return. It
round-trips canonical ternary IR and requires the independently witnessed
97-step guest output; other values, profiles or effects reject.

The `--distinct-literal-thirty-three` typed mode binds 33 independent `u8`
constant/byte-output SSA pairs and a void return to the source-proven witness.
Canonical typed IR and ternary IR retain their provenance; wrong profiles,
SSA uses, values and lengths reject before the 97-step real-VM preflight.

The `--distinct-literal-thirty-four` typed mode re-admits exactly 34
independent constant/output SSA pairs before real guest execution.

The `--distinct-literal-thirty-five` typed mode re-admits exactly 35
independent constant/output SSA pairs before real guest execution.

The `--distinct-literal-thirty-six` typed mode independently re-admits
36 exact `u8` SSA materializations and outputs, then requires real-VM proof.

The `--distinct-literal-thirty-seven` typed mode revalidates 37 independent
`u8` constant/byte-output SSA pairs against the exact normative VM witness.

The 38-byte typed witness independently admits 38 unique `u8` SSA pairs and
requires the 97-step guest arithmetic proof before publication.


The 39-byte typed mode separately validates 39 fresh `u8` constant/output
SSA pairs before releasing the normative 97-step guest execution.

The 40-byte typed mode requires 40 fresh exact `u8` SSA materializations
and outputs; independently validated ternary and real VM evidence must agree.

The exact 41-byte C output witness now projects source-bound canonical
typed IR into MCTR and the separately verified real-guest arithmetic
bridge. No general byte stream or guest ABI is implied.

The exact 42-byte source effect sequence projects typed IR into canonical
MCTR and the independently verified guest arithmetic bridge. All SSA
identities and source-order byte values remain strictly checked.
