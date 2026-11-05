# Byte Echo Bridge

## Purpose

Prove one small executable end-to-end compiler slice without weakening the
canonical pre-layout ternary model or the independently admitted graphical
Malbolge encoder.

## Ownership

`composition/lib.rs` first admits a one-function, value-free-return program
with adjacent `ByteInput`/`ByteOutput` pairs, using the same SSA byte identity
in each pair. `encode_successful_byte_echo` retains that strict historical
behavior without any widened effect admission.

A separately selected `encode_successful_latest_byte_trace` admits a broader
validated one-function void trace: one or more `ByteInput` effects and any
number of `ByteOutput` effects, provided each output refers to the **most
recent** input's exact SSA byte identity. One input may be output repeatedly
or not at all. The normative VM accumulator preserves its value across
outputs and is overwritten by each new input. Reading a new byte therefore
invalidates replay of an older SSA input; the new API rejects that case.

All separately selected APIs revalidate the complete canonical ternary
program, match the profile, and delegate source encoding/admission to
`malbolge-layout`. They
emit the actual source code; no host callback performs guest byte I/O.

### Verified side-effect-free void function

`encode_empty_void_function` accepts exactly one canonical current-profile
MCTR function containing only `ReturnVoid`. It emits a graphical no-op and
real halt, the minimum two cells admitted by the loader. The selected VM
performs two steps with no output or input consumption. Nonempty operations,
foreign profiles, non-void returns and malformed MCTR reject. This proves an
observable absence of byte effects, not general C source compilation,
function calls, non-void returns or process exit semantics. The typed adapter
and `malbolge_layout --empty-void` publisher admit the same exact subset.


An independent, explicitly selected library entrypoint,
`encode_initial_zero_outputs`, admits exactly one canonical MCTR void
function whose first effect is `MaterializeU8(0)` with one fresh SSA ID,
followed by **one or more** `ByteOutput` uses of that *same* value and a final
`ReturnVoid`. The generated source has no input: the normative VM's initial
accumulator is exactly zero, so the declarative zero scalar needs no guest
mutation instruction. Each effect is an actual guest output instruction,
followed by a real halt. No host printing or fabricated byte register is
used. Original source/SSA/span provenance remains in the admitted MCTR.

`tests/zero_output_bridge.rs` independently lowers and re-decodes canonical
MCTR, checks exact guest output of 1, 2, 7 and 64 zeros with **zero** input
consumption, executes the 4096-cell maximum (4095 output bytes plus halt),
and rejects the next cell, nonzero constants, absent outputs, extra valid
constant materialization, undefined SSA, and profile drift. Existing
adjacent-echo and latest-read APIs remain closed to this shape. MCTR-v1 is
pinned to the current `malbolge-2026` target; the library API does not
extend historical/versioned typed source admission.

The initial-zero-only library entrypoint also has a separate, opt-in
canonical MCTI adapter and `malbolge_layout` CLI publisher. Neither it nor
the mixed zero-prefixed latest-byte mode realizes arbitrary nonzero byte
constants, heap, guest libc linkage or EOF semantics.

### Verified zero-prefixed latest-successful-byte trace

A fourth, independently selected bridge,
`encode_zero_prefixed_latest_byte_trace`, composes **two** already proven
accumulator phases in one genuine guest program. One canonical `u8`
`MaterializeU8(0)` SSA is followed by at least one output of that same zero
value, then at least one successful byte input and at least one output of
the most recent input SSA. Any subsequent input overwrites A again and
only outputs of its exact SSA result are permitted. There is no memory
copy, host printing or synthetic accumulator reset: after the first input,
the initial zero SSA cannot be output again. Its source is `OutputByte`,
`InputWord`, `OutputByte`, and final `Halt`, with no instruction for the
proved initial-zero materialization. Full canonical MCTR, function/SSA,
profile and address-sensitive layout admission precedes source emission.

The new `tests/zero_prefix_trace_bridge.rs` validates independent canonical
wire re-admission, genuine VM output with bytes `0x00`, `0xff`, and `0x80`,
real input consumption, and exactly 4096 source cells. It refuses missing
zero prefix/read/latest-read output, nonzero or extra valid constants,
post-read zero SSA replay, prior-read SSA replay, profile drift and one
cell over the target bound. The original strict echo, latest-read and
initial-zero-only APIs are unchanged. The new mixed trace is deliberately
not a general byte SSA register file, arithmetic lowering, heap or EOF.

### Verified live byte-bitcast aliases

The opt-in `encode_latest_byte_identity_trace` admits real successful-byte
input/output with canonical MCTR `BitcastU8ToI8`, `BitcastI8ToI8`,
`BitcastI8ToU8` and `BitcastU8ToU8` SSA effects. These are exact
representation-only eight-bit aliases of the current accumulator; they
produce no guest machine instruction. Outputs can name any live `u8`
alias of the most recent input, including the original input SSA ID.
Every subsequent input invalidates all previous aliases. A later cast or
output of stale SSA cannot be reloaded without guest storage, and rejects.

The bridge requires at least one input, one identity bitcast, one output,
one final void return, complete canonical re-admission and selected-profile
layout. An explicit bounded 4096-effect projection yields at most 4096
actual guest code cells. The independent `byte_identity_trace_bridge`
regression proves all four bitcasts, real 0/255/128 VM bytes, stale replay,
profile mismatch, original strict/latest unchanged, and capacity limits.
No host guest-byte simulation, general integer operation, EOF or guest ABI
is implied.

### Verified nonzero byte literal rotation

The separate opt-in `encode_rotated_byte_literal` admits exactly one
`MaterializeU8(value)`, one to thirty-three `ByteOutput`s of that SSA
identity, and `ReturnVoid`. For one output, 34 verified
current-profile nonzero bytes are available: `4, 5, 6, 9, 10, 11, 12, 13,
14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 25, 29, 36, 37, 38, 39, 43, 44,
157, 158, 159, 160, 161, 162, 251, 253`. The additional 20 values have
independently checked prefix lengths between 27 and 64; no value is inferred
from a different output count. Separately, exact one-output witnesses use
guest `p` crazy operations after data relocation rather than rotation. The
current-profile bytes and no-op
prefixes are `5` (53/39), `6` (54/22), `8` (56/36), `9` (57/19),
`>` (62/30), `?` (63/47), `A` (65/27), `B` (66/65), `P` (80/3),
`Q` (81/11), `S` (83/0), `T` (84/7), `Z` (90/1), and `]` (93/28).
The `B` guest has 69 source cells. Three separately witnessed single-output
bytes use **two** real guest rotations after relocation: `(` (40/51),
`)` (41/48), and `*` (42/45), shown as byte/no-op-prefix pairs. Their distinct
source lengths and two data writes cannot be inferred from one-rotation
witnesses. Every witness is re-executed with the normative VM on each bridge
invocation, and none authorizes another byte, output count, or profile.
An independently selected `encode_zero_then_literal` path now admits exactly
two *different* source-proven constant outputs: first NUL then one of
`Z`, `P`, `T`, or `S`. The actual current-profile guest emits initial zero,
executes a relocated `p` crazy operation and emits the chosen second byte.
Their exact no-op prefixes are 0/2/6/17, producing 5/7/11/22 guest
steps. Both constant SSA identities and complete effect order are checked
against re-admitted MCTR, and the normative VM verifies both bytes across
empty and supplied input before returning the graphical source. This is a
distinct opt-in bridge, not a widening of the repeated-identical-byte path;
unsupported bytes, extra outputs and old-value reuse remain rejected.

For exactly two identical outputs, a **different** table
admits `55, 64, 65, 66, 163, 164, 165, 182, 183, 200`. For exactly three
identical outputs, an independently witnessed table admits `3, 4, 5, 6, 7,
8, 9, 11, 18, 19, 20, 21, 22, 23, 24, 25, 144, 145, 146, 251, 252`.
For exactly four identical outputs, a separately checked table admits
`40, 41, 42, 43, 44, 57, 64, 65, 66, 161, 162, 168, 175, 176, 178, 182,
184, 185, 186, 187, 191, 192, 196, 201`. For exactly five identical
outputs, 18 independently verified values are `4, 6, 7, 8, 9, 10, 12,
21, 22, 23, 24, 25, 137, 138, 139, 140, 141, 142`. For exactly six
outputs, 19 distinct witnessed bytes are `40, 41, 42, 47, 61, 63, 64, 65,
66, 162, 175, 176, 177, 178, 185, 186, 190, 191, 200`. For exactly
seven outputs, 18 distinct witnessed bytes are `4, 5, 6, 7, 8, 9, 10, 12,
16, 17, 18, 19, 20, 21, 22, 23, 251, 253`. For exactly eight
outputs, 21 distinct witnessed bytes are `40, 41, 42, 55, 56, 57, 64, 65,
66, 161, 162, 163, 175, 176, 177, 178, 197, 198, 199, 200, 201`.
For exactly nine outputs, 21 witnessed values are `1, 2, 3, 4, 5, 6,
7, 9, 10, 11, 18, 19, 20, 21, 22, 23, 142, 143, 144, 251, 252`.
For exactly ten outputs, 25 witnessed values are `40, 41, 42, 55, 56,
57, 64, 65, 66, 161, 162, 176, 178, 182, 183, 184, 185, 186, 187,
191, 192, 193, 196, 200, 201`.
For exactly eleven outputs, 17 witnessed values are `4, 6, 7, 8, 9,
10, 12, 21, 22, 24, 25, 135, 136, 137, 138, 139, 140`.
For exactly twelve outputs, 20 witnessed values are `40, 41, 56, 60, 61,
62, 63, 64, 65, 66, 176, 177, 178, 180, 184, 185, 186, 190, 191, 200`.
For exactly thirteen outputs, 19 distinct witnessed values are `4, 5, 6,
7, 8, 9, 10, 12, 14, 15, 16, 17, 18, 19, 20, 21, 22, 251, 252`.
For exactly fourteen outputs, 22 distinct witnessed values are `41, 49,
51, 55, 56, 57, 59, 64, 65, 66, 162, 176, 178, 185, 187, 192,
193, 195, 197, 198, 199, 200`. For exactly fifteen outputs, 17
distinct witnessed values are `1, 2, 3, 4, 6, 8, 10, 11, 18, 21, 22,
23, 140, 141, 142, 251, 255`. For exactly sixteen outputs,
24 distinct VM-verified bytes are `41, 49, 51, 55, 56, 57, 64, 65, 66,
176, 177, 178, 179, 181, 182, 183, 184, 186, 193, 194, 195, 196,
200, 201`.
For exactly seventeen outputs, the independent 26-phase VM scan yields
19 distinct nonzero bytes: `4, 5, 6, 7, 9, 12, 19, 20, 22, 24, 25,
133, 134, 135, 136, 137, 138, 251, 253`.
For exactly eighteen outputs, all 26 independently VM-executed phases
produce 20 distinct nonzero bytes: `55, 56, 58, 59, 60, 61, 62, 63, 64,
65, 66, 179, 180, 184, 185, 186, 190, 191, 200, 201`.
For exactly nineteen outputs, all 26 independently VM-executed phases
produce 19 distinct nonzero bytes: `3, 4, 5, 6, 7, 8, 9, 10, 12, 13, 14,
15, 16, 17, 18, 19, 20, 251, 252`.
For exactly twenty outputs, all 26 independently executed source phases
produce 21 distinct nonzero bytes: `48, 49, 50, 51, 55, 56, 58, 59, 64,
65, 184, 185, 186, 191, 192, 193, 194, 195, 196, 197, 198`.
For exactly twenty-one outputs, 25 of 26 independent VM phases succeed
(phase fourteen is excluded), yielding 20 distinct nonzero values: `1, 2,
4, 7, 8, 9, 10, 11, 12, 21, 22, 23, 25, 138, 139, 140, 252, 253,
254, 255`. Twenty-two outputs admit all 26 phases and 25 distinct
nonzero bytes: `18, 48, 49, 50, 51, 55, 56, 63, 64, 65, 169, 177,
179, 180, 181, 182, 183, 186, 190, 191, 193, 194, 195, 196, 200`.
Twenty-three outputs independently witness 21 distinct nonzero bytes:
`4, 6, 7, 8, 9, 10, 12, 17, 18, 21, 22, 24, 25, 27, 42,
132, 133, 134, 135, 136, 251` across all 26 successful phases.
Twenty-four outputs admit 21 bytes from 25 successful phases, excluding
phase seven; twenty-five outputs likewise admit 25 phases (not seven),
with 19 distinct bytes: `2, 3, 6, 7, 8, 9, 11, 12, 13, 14, 15, 18,
22, 23, 29, 39, 44, 162, 253`. For twenty-six outputs,
22 independently witnessed values are `20, 21, 47, 48, 49, 50, 51, 55,
57, 58, 59, 65, 137, 139, 156, 182, 184, 193, 194, 195, 196, 201`;
24 phases pass, with phases six and seven excluded.
For twenty-seven outputs, 23 independently guest-verified phases pass
(excluding six, seven and eight), yielding 18 distinct bytes: `7, 8, 9,
11, 21, 22, 23, 25, 41, 42, 137, 138, 164, 165, 252, 253, 254, 255`.
For twenty-eight outputs, 23 independent VM phases pass (not five,
six or seven), yielding 22 shortest distinct bytes: `18, 19, 21, 48,
49, 50, 51, 61, 63, 140, 141, 151, 153, 169, 179, 180, 181, 185,
191, 194, 195, 196`. Byte 191 repeats at phase four, so phase one wins.
Twenty-nine outputs pass 23 short VM phases (not five through seven),
retaining 19 distinct shortest values: `6, 7, 8, 9, 10, 12, 16,
21, 22, 25, 26, 27, 42, 43, 132, 133, 134, 164, 165`.
Phases eleven, twelve, seventeen and twenty-four repeat shorter seeds.
Thirty outputs pass 22 short phases (not four through seven), admitting
20 distinct nonzero bytes: `15, 16, 18, 19, 21, 48, 55, 56, 58, 59,
64, 150, 154, 155, 168, 179, 180, 185, 187, 197`. Byte 185 repeats
at phase eleven and byte 21 at phase eighteen, retaining earlier seeds.
Thirty-one outputs pass 22 of 26 phases (not four through seven),
retaining 19 shortest nonzero bytes: `1, 6, 7, 8, 10, 11, 12, 13, 21,
22, 25, 29, 39, 43, 44, 160, 161, 162, 253`. Bytes 7, 29 and 39
repeat, so their earliest safe source prefix is retained.
Thirty-two outputs pass 21 of 26 phases (excluding three through seven),
retaining 20 distinct shortest nonzero bytes: `15, 19, 20, 21, 47, 48,
50, 56, 58, 59, 136, 137, 139, 150, 154, 156, 183, 194, 196, 200`.
Byte 139 repeats at phase 25; its shorter phase-16 witness is retained.
Thirty-three outputs pass 21 of 26 phases (excluding three through seven),
retaining 18 shortest nonzero bytes: `7, 9, 11, 21, 24, 39, 40, 41, 42,
136, 158, 159, 160, 164, 165, 252, 253, 254`. Bytes 160 and 164
repeat; their first successful phases 21 and 16 are retained.
The bridge keeps each byte's first valid no-op prefix and rechecks it
under the actual guest VM before returning executable source.

A profile-specific *proposed* no-op prefix precedes `j`, `*`, the actual
`<` outputs, and `v`. The canonical loader expands the complete graphical
source into guest memory. Changing the output count changes the positional
encoding and the loader-expanded data; therefore seeds are admitted per
exact output count, not reused across modes. The guest `*` rotates its real
data word into A, and the
guest outputs emit the unchanged accumulator. The independent layout checker
proves source/data separation and a fresh normative VM checks every emitted
byte, exact halt, and zero input consumption before accepting a source.
Other literals, zero/thirty-four-or-more outputs, extra effects and foreign
profiles reject.
This does not implement arbitrary constants or an SSA byte register.

The three-output witnesses derive from a bounded independent scan of no-op
prefix lengths `0..26` (not an exhaustive search of all 94 phases): an
independently admitted `j`, `*`, three `<` operations and `v` must halt
on the real VM with exactly three equal nonzero output bytes and no input.
The 26 successful phases yield 21 distinct bytes, retaining the shortest
witness for each. Reproduce the deliberately slower independent search with:

```sh
cargo test --release --locked --test rotated_byte_constant_bridge \
  independently_rederive_three_output_rotation_witnesses -- --ignored
```

The four-output witnesses independently scan the same `0..26` source-prefix
range with four consecutive guest `<` instructions; all 26 phases halt with
four identical nonzero outputs and yield 24 distinct values. The seed table
retains the first, shortest successful prefix for each value. Reproduce via:

```sh
cargo test --release --locked --test rotated_byte_constant_bridge \
  independently_rederive_four_output_rotation_witnesses -- --ignored
```

The five-output witness scan uses the same `0..26` bounded no-op prefixes
with five real guest outputs. All 26 phases terminate with identical nonzero
bytes, yielding 18 distinct values. Each value retains its first (shortest)
witness, independently replayed by the target bridge. Reproduce via:

```sh
cargo test --release --locked --test rotated_byte_constant_bridge \
  independently_rederive_five_output_rotation_witnesses -- --ignored
```

Six- through thirty-three-output witnesses independently repeat the same bounded
`0..26` scan, with their own loader-expanded source. All 26 tested phases
for each count through fourteen emit identical nonzero bytes and terminate
without input. Fifteen outputs have 25 matching phases; phase 20 does
not yield an admissible witness. All 26 sixteen-output phases match,
with 24 distinct nonzero byte values independently checked by the VM.
All 26 seventeen-output phases also halt with matching nonzero bytes,
producing 19 distinct values. All 26 eighteen-output phases likewise
halt with 18 equal nonzero bytes and zero input, yielding 20 unique values.
All 26 nineteen-output phases halt with 19 equal nonzero bytes and zero
input, yielding 19 unique values. Twenty outputs yield 21 distinct nonzero
bytes from 26 terminating phases with exact repeated output.
Twenty-one outputs admit 25 of 26 phases (not phase fourteen), retaining
20 distinct bytes after dropping duplicate values.
All 26 twenty-two-output phases produce matching nonzero bytes, with
25 distinct values and a duplicate at phase ten. Twenty-three outputs
also have 26 successful phases and 21 distinct byte values, preserving
the earliest prefix even where later phases repeat 9, 22 or 7.
Twenty-four outputs succeed in 25 of 26 real VM phases (phase seven fails),
and retain 21 distinct shortest byte witnesses from those valid phases.
Twenty-five outputs also succeed in 25 phases (excluding seven), yielding
19 distinct nonzero values with shortest safe prefixes.
Twenty-six outputs succeed in 24 of 26 phases, excluding six and seven,
and retain 22 distinct shortest witnesses. Twenty-seven outputs admit 23
of 26 phases (not six, seven or eight), retaining 18 distinct shortest
witnesses. Twenty-eight outputs succeed in 23 phases (not five,
six or seven), retaining 22 distinct shortest byte witnesses.
Twenty-nine outputs pass 23 phases (not five through seven),
retaining 19 shortest distinct byte witnesses.
Thirty outputs pass 22 phases (excluding four through seven),
retaining 20 shortest distinct byte witnesses (185 and 21 repeat).
Thirty-one outputs also pass 22 phases, excluding four through seven,
and yield 19 distinct shortest witnesses (7, 29 and 39 repeat).
Thirty-two outputs pass 21 phases (excluding three through seven),
retaining 20 shortest values (139 repeats).
Thirty-three outputs pass 21 phases (excluding three through seven),
retaining 18 shortest values (164 repeats twice, 160 once).
The first successful witness per value yields
19 shortest prefixes for six outputs, 18 for seven, 21 for eight, 21 for
nine, 25 for ten, 17 for eleven, 20 for twelve, 19 for thirteen, 22 for
fourteen, 17 for fifteen, 24 for sixteen, 19 for seventeen, 20 for
eighteen, 19 for nineteen, 21 for twenty, 20 for twenty-one and
25 for twenty-two, 21 for twenty-three, 21 for twenty-four and
19 for twenty-five, 22 for twenty-six, 18 for twenty-seven and
22 for twenty-eight, 19 for twenty-nine, 20 for thirty and
19 for thirty-one, 20 for thirty-two and 18 for thirty-three.
Reproduce the independent optimized scans with:

```sh
cargo test --release --locked --test rotated_byte_constant_bridge \
  independently_rederive_six_output_rotation_witnesses -- --ignored
cargo test --release --locked --test rotated_byte_constant_bridge \
  independently_rederive_seven_output_rotation_witnesses -- --ignored
cargo test --release --locked --test rotated_byte_constant_bridge \
  independently_rederive_eight_output_rotation_witnesses -- --ignored
cargo test --release --locked --test rotated_byte_constant_bridge \
  independently_rederive_nine_output_rotation_witnesses -- --ignored
cargo test --release --locked --test rotated_byte_constant_bridge \
  independently_rederive_ten_output_rotation_witnesses -- --ignored
cargo test --release --locked --test rotated_byte_constant_bridge \
  independently_rederive_eleven_output_rotation_witnesses -- --ignored
cargo test --release --locked --test rotated_byte_constant_bridge \
  independently_rederive_twelve_output_rotation_witnesses -- --ignored
cargo test --release --locked --test rotated_byte_constant_bridge \
  independently_rederive_thirteen_output_rotation_witnesses -- --ignored
cargo test --release --locked --test rotated_byte_constant_bridge \
  independently_rederive_fourteen_output_rotation_witnesses -- --ignored
cargo test --release --locked --test rotated_byte_constant_bridge \
  independently_rederive_fifteen_output_rotation_witnesses -- --ignored
cargo test --release --locked --test rotated_byte_constant_bridge \
  independently_rederive_sixteen_output_rotation_witnesses -- --ignored
cargo test --release --locked --test rotated_byte_constant_bridge \
  independently_rederive_seventeen_output_rotation_witnesses -- --ignored
cargo test --release --locked --test rotated_byte_constant_bridge \
  independently_rederive_eighteen_output_rotation_witnesses -- --ignored
cargo test --release --locked --test rotated_byte_constant_bridge \
  independently_rederive_nineteen_output_rotation_witnesses -- --ignored
cargo test --release --locked --test rotated_byte_constant_bridge \
  independently_rederive_twenty_output_rotation_witnesses -- --ignored
cargo test --release --locked --test rotated_byte_constant_bridge \
  independently_rederive_twenty_one_output_rotation_witnesses -- --ignored
cargo test --release --locked --test rotated_byte_constant_bridge \
  independently_rederive_twenty_two_output_rotation_witnesses -- --ignored
cargo test --release --locked --test rotated_byte_constant_bridge \
  independently_rederive_twenty_three_output_rotation_witnesses -- --ignored
cargo test --release --locked --test rotated_byte_constant_bridge \
  independently_rederive_twenty_four_output_rotation_witnesses -- --ignored
cargo test --release --locked --test rotated_byte_constant_bridge \
  independently_rederive_twenty_five_output_rotation_witnesses -- --ignored
cargo test --release --locked --test rotated_byte_constant_bridge \
  independently_rederive_twenty_six_output_rotation_witnesses -- --ignored
cargo test --release --locked --test rotated_byte_constant_bridge \
  independently_rederive_twenty_seven_output_rotation_witnesses -- --ignored
cargo test --release --locked --test rotated_byte_constant_bridge \
  independently_rederive_twenty_eight_output_rotation_witnesses -- --ignored
cargo test --release --locked --test rotated_byte_constant_bridge \
  independently_rederive_twenty_nine_output_rotation_witnesses -- --ignored
cargo test --release --locked --test rotated_byte_constant_bridge \
  independently_rederive_thirty_output_rotation_witnesses -- --ignored
cargo test --release --locked --test rotated_byte_constant_bridge \
  independently_rederive_thirty_one_output_rotation_witnesses -- --ignored
cargo test --release --locked --test rotated_byte_constant_bridge \
  independently_rederive_thirty_two_output_rotation_witnesses -- --ignored
cargo test --release --locked --test rotated_byte_constant_bridge \
  independently_rederive_thirty_three_output_rotation_witnesses -- --ignored
```

Default regressions enumerate all 256 byte values separately for four,
five, six, seven, eight, nine, ten, eleven, twelve, thirteen, fourteen,
fifteen, sixteen, seventeen, eighteen, nineteen, twenty, twenty-one,
twenty-two, twenty-three, twenty-four, twenty-five, twenty-six,
twenty-seven, twenty-eight, twenty-nine, thirty, thirty-one, thirty-two and thirty-three same-SSA outputs.
They require 24, 18, 19, 18, 21, 21, 25, 17, 20, 19, 22, 17, 24, 19,
20, 19, 21, 20, 25, 21, 21, 19, 22, 18, 22, 19, 20, 19, 20 and 18 shortest prefixes,
respectively. The other
232, 238, 237, 238, 235, 235, 231, 239, 236, 237, 234, 239, 232,
237, 236, 237, 235, 236, 231, 235, 235, 237, 234, 238,
234, 237, 236, 237, 236 and 238 values reject.
The canonical typed adapter, CLI publisher and real guest runner verify
successful and rejected count-specific cases.

## Limits

The trace is equivalent **only on successful byte I/O**: every input must
provide a byte rather than EOF, and every output must succeed. The final void
return is process termination; guest calling-convention state, status codes,
EOF/error semantics, arithmetic, stale-SSA byte replay, globals and multiple
functions are not realized. The new API has no guest byte storage and does not
implement general nonadjacent dataflow, branching or byte transformation.
A validated trace must fit two to 4096 exact instruction cells, including
halt.
Rejections are explicit, not fallback emulation.

## Validation

`cargo test --locked --test byte_echo_bridge` executes the generated source in
the normative current-profile VM and checks the exact input/output trace, as
well as profile drift, oversized trace admission and unsupported-effect
rejection. An independently admitted canonical typed-IR byte-I/O function
round-trips through typed-IR and ternary wire formats before VM execution.
One 513-cell machine trace also executes all 256 possible successful byte
values exactly, including `0x00` and `0xff` (which is data, not EOF).

`cargo test --locked --test byte_io_trace_bridge` independently round-trips
canonical ternary IR and executes repeat-output, consumed-without-output,
and mixed newest-input traces on the real normative VM. It verifies duplicate
output for all 256 bytes, exact old echo source compatibility, and a 4096-cell
single-input/4094-output boundary. It rejects prior-input SSA replay after a
newer input, unsupported scalar/return, changed profile, malformed program
and one cell beyond the maximum. The new API is a bounded integration witness,
not a general C-to-Malbolge backend or raw-file publisher.

An independent two-nonzero-byte route admits only `Y/`, `Y$`, and `Q.` under
the current profile. A relocated data pointer feeds two separate guest `p`
operations on separate guest data words, recomputing the accumulator before
each `<` output. The position-dependent source lengths are 6, 7, and 8
cells. These are independently VM-replayed witnesses, not arbitrary byte-pair
support.

### Three different source-proven guest byte outputs

The separate `encode_distinct_literal_triple` bridge accepts the exact
current-profile triples `Z%H`, `Q.O`, `Y-P`, `T"O`, and `T"Q`. A single
`j` relocates
data beyond the source; three independent `p` guest writes each precede
an output. The verified source lengths and exact guest step counts are
8, 9, 10, 12, and 14 respectively. Three independent `u8` SSA constants and
three matching output uses must survive canonical MCTR admission. The
layout verifier checks each data-write address and the independent VM
replays with empty and nonempty input. No arbitrary three-byte sequences,
EOF, guest ABI, or host-side output substitution are implied.
`tests/guest_distinct_literal_triplet.rs` exercises the actual guest VM.

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

The `--distinct-literal-twenty-three` C path admits the exact source-ordered
bytes `42 0e 2f 17 39 04 8e 24 9f 1b a0 23 97 15 28 27 29 14 32 1e
8b 26 92` (hex). Eight reached no-ops precede relocation, followed by twenty
`CrazyData` and three `RotateData` writes (positions 7, 14 and 21), then one
reached no-op and halt. The real VM verifies all 23 bytes in 57 steps with
zero consumed input before artifact publication. Arbitrary byte strings
remain unsupported.

The `--distinct-literal-twenty-four` C path admits exactly the source-ordered
bytes `3e 0b 2c 12 36 01 3d 95 0f 9d 17 8b 21 93 92 20 94 0e 9b 18
8a 1c 2f 23` (hex). Twenty-one reached no-ops precede data-pointer
relocation; twenty-one `CrazyData` writes and three `RotateData` writes
(positions 8, 15, 22) produce 24 distinct output bytes. The normative
VM verifies 72 steps and zero input consumption before raw/capsule emission.
Arbitrary 24-byte output remains unsupported.

The `--distinct-literal-twenty-five` C path admits exactly the 25
source-ordered bytes `51 3e 35 38 54 1f 4e 33 3d 39 05 53 23 1b b5 2c
cb 12 c6 2e af b4 f8 ca 0e` (hex). Twenty-six reached no-ops precede
relocation; 22 `CrazyData` and three `RotateData` guest writes compute 25
distinct output bytes. Twenty-seven trailing no-ops preserve the proven
105-step source recurrence. The real VM verifies exact byte output, zero
input consumption, and nonoverlapping source/data before publication.
Arbitrary 25-byte output remains unsupported.

The `--distinct-literal-twenty-six` source mode admits the exact 26-byte
prefix of the independently proven 28-byte guest arithmetic trace:
`51 3e 35 38 54 1f 4e 33 3d 39 05 53 23 1b b5 2c cb 12 c6 2e
af b4 f8 ca 0e 95` (hex). Twenty-six reached no-ops precede relocation;
23 `CrazyData` and three `RotateData` writes emit distinct bytes. A 25-
no-op tail preserves the 105-cell source recurrence, with all writes beyond
the source, zero stdin consumed and exact 105-step normative termination.
Arbitrary 26-byte source strings remain unsupported.

The `--distinct-literal-twenty-seven` C source path admits precisely the
27-byte prefix of the independently checked 28-byte guest arithmetic witness:
`51 3e 35 38 54 1f 4e 33 3d 39 05 53 23 1b b5 2c cb 12 c6 2e af b4
f8 ca 0e 95 2d` (hex). Twenty-six reached no-ops relocate the guest data
pointer; 24 `CrazyData` and three `RotateData` writes compute 27 distinct
binary outputs. Twenty-three trailing no-ops preserve the 105-step source
recurrence, and independent real-VM replay rejects any unsupported source.
Arbitrary 27-byte output remains unavailable.

The `--distinct-literal-twenty-eight` compiler path admits exactly the
28-byte source prefix of the independently verified arithmetic witness:
`51 3e 35 38 54 1f 4e 33 3d 39 05 53 23 1b b5 2c cb 12 c6 2e af b4
f8 ca 0e 95 2d ab` (hex). Twenty-six reached no-ops precede relocation;
25 guest `CrazyData` and three `RotateData` writes compute distinct outputs.
Twenty-one trailing no-ops retain the 105-step recurrence, and a normative
VM replay rejects unproved effects. Other 28-byte traces remain unsupported.

An independent **twenty-nine-byte physical guest witness** is verified by
`tests/guest_twenty_nine_distinct_literal_witness.rs`. Nine initial no-ops,
a data relocation, and one interleaved no-op before the second arithmetic
pair produce 29 distinct bytes using four guest rotates (indices zero, eight,
fifteen, and twenty-two) and 25 guest crazy writes. The 105-step normative VM
executes all 29 writes at addresses 126, 129, 131–183 outside the 105-cell
source, emits `87 b7 bc b1 8a ce 9f 9c b5 2c cb 12 c6 2e af b4 f8 ca
0e 95 2d ab 33 3d 39 05 53 23 1b` (hex), and consumes no input. The exact trace
now also has a **bounded C-to-Malbolge compiler path**. Pinned Clang AST
admission accepts the exact 29 source-ordered `putchar` constants only. The
typed adapter projects 29 separate `u8` SSA values through canonical MCTR and
`encode_distinct_literal_twenty_nine`; independent 105-step VM preflight checks
exact output and zero consumed input before raw/capsule publication. Positive
and rejection tests are in the C29 integration regression
`tests/test_c2malbolge_distinct_literal_twenty_nine.py` and the ternary
regression `tests/guest_twenty_nine_ternary_bridge.rs`. This does not provide general C byte-stream compilation or a retained 29-byte example corpus yet.

An independent **thirty-byte physical guest witness** is now verified by
`tests/guest_thirty_distinct_literal_witness.rs`. Thirty-four reached no-ops
precede a `j` data relocation at source position 34; one reached no-op
precedes arithmetic pair four. Four `RotateData` operations (zero-based
indices 1, 10, 17 and 24) and 26 `CrazyData` operations modify 30 distinct
data cells at addresses 101, 103, 105, 108–160 (every second address), all
outside the 97-cell source. The normative current-profile VM runs exactly
97 steps, emits `39 a8 07 da 99 dd a3 cf a7 d9 09 d4 ac e1 9e e2 ab
0b d6 9c e3 a0 d2 ad 93 e0 9f e4 aa d5` (hex), and consumes zero input.
This source-independent arithmetic proof does not yet admit any 30-byte
C program through the compiler or establish general byte-stream lowering.

The exact 30-byte guest witness is now also compiled from pinned C
`putchar` literals through canonical typed IR and independently re-admitted
ternary IR. The source-bound bridge verifies four rotations, 26 crazy
writes, 30 distinct guest outputs, 97 steps and zero consumed input.
`tests/test_c2malbolge_distinct_literal_thirty.py` confirms raw/capsule
execution, invalid-prefix refusal, unchanged prior Q. output and no-clobber
publication. Other 30-byte streams remain unsupported.

The independent 31-byte source-bound bridge now encodes one exact
31-materialization/31-output ternary trace with a void return. Its 73-cell
current-profile guest computes all 31 bytes through 26 crazy and five rotate
writes, with a reached no-op shifting the loader phase. Profiles, effects and
SSA are verified before the real VM checks the exact output and zero input
consumption. No general arbitrary-byte C lowering is implied.

The independent 32-byte source-bound bridge requires 32 distinct
constant/output SSA pairs and a void return. The 97-cell guest layout uses
30 leading no-ops, a relocated data pointer, and one internal no-op before
its fifth byte pair; 29 crazy writes and three rotates at byte indices
11, 18 and 25 compute all 32 bytes with zero guest input consumed. The
exactly matched source and normative VM output are required for admission.
Other 32-byte traces remain unsupported.

The independent 33-byte source-bound bridge admits only the exact
33-materialization/33-output ternary trace. Twenty-eight leading no-ops
precede data relocation, with one reached no-op before byte index six. Thirty
crazy writes and three rotations at indices 13, 20 and 27 compute all distinct
bytes. The 33 data writes at 107..172 are disjoint from the 97-cell source;
profile, SSA and normative VM output must agree before any publication.

A separately VM-proven 34-byte output trace uses 30 crazy writes and four
rotations in a 97-step layout; no general C output is implied.

A separately VM-proven 35-byte output trace uses 30 crazy writes and five
rotations in a 97-step layout; no general C output is implied.

The 36-byte witness computes 31 crazy and five rotate writes in 97 steps.
All 36 guest data writes stay outside encoded source, and two input patterns
confirm zero consumed input and exact byte output.

The 37-byte witness realizes 32 crazy and five rotate operations in 97
real-VM steps. Its 37 data writes lie outside the 97-cell guest source.

The 38-byte witness executes 33 `CrazyData` and five `RotateData` writes in
97 real VM steps, with 38 disjoint data addresses outside source memory.


The 39-byte guest arithmetic witness uses 33 crazy and six rotate writes
in 97 steps; two inert internal no-ops preserve source/data separation.

The 40-byte independent ternary bridge admits only the exact proven binary
materializations and SSA outputs. Fourteen initial no-ops, one internal no-op
and six rotations give 40 disjoint guest writes in 97 real VM steps.
This does not enable 40-byte C source compilation.
