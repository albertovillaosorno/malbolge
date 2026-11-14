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

The current-profile distinct two-byte route now searches a bounded 94-phase
linear grammar instead of selecting just `Y/`, `Y$`, and `Q.` from a fixed
witness table. Each output follows a guest `p` (crazy) or `*` (rotate)
operation after one safe `j` relocation; the two data writes are disjoint
and out of source. An untrusted decoder/loader preview filters candidates,
but independent layout admission and two normative VM replays authorize each
emitted source. The three original pairs retain byte-exact layouts. The
new binary witness `02 cf` uses 26 reached no-ops, `j`, `*`, `<`, `p`, `<`,
`v`; a source-proven two-iteration conditional C loop emits the same bytes
through the complete compiler. Other byte pairs can still fail closed: this
is a bounded synthesis grammar, not general guest byte-stream lowering.
The adjacent equal-value pair `38 38` is a separately admitted case: two
source-bound SSA outputs become two guest output instructions after one
verified relocated arithmetic write. Equal values do not imply shared SSA
provenance, nor does this authorize arbitrary repeated nonzero byte streams.

### Three source-proven guest byte outputs

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

The same bounded three-write grammar now admits nonadjacent equal outputs
such as `Z%Z` when the guest independently computes the first and third
bytes. An adjacent repeat may reuse a live accumulator, but a nonadjacent
repeat may not: all three arithmetic writes must be disjoint and outside
the source. The independent publisher re-decodes the staged bytes, checks
the layout and VM output on two inputs, and rejects an altered effect trace.
This does not imply arbitrary three-byte strings or runtime C loop execution.

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

The opt-in `--distinct-literal-quint` mode retains its historical source
witness `51 22 1b 37 39` (hex: `Q`, quote, ESC, `7`, `9`). Its eleven-nop
relocated target performs five disjoint guest `CrazyData` writes and five
byte outputs in 23 normative VM steps. A separate source-independent
state-space search now accepts an initial zero output before relocation,
then four arithmetic-derived byte outputs. A complete source-C probe with
five separate `putchar` effects emits `00 54 3d 34 3e` (`NUL T=4>`) under
the normative guest VM on both empty and nonempty input. The pinned Clang
adapter still restricts this source path to the exact witnessed zero-first
sequence; the lower bridge searches other zero-first traces but publishes
only independently verified layouts within its finite source-state budget.
Canonical typed/MCTR identity, five distinct SSA bindings, relocated writes,
no input consumption and raw/capsule replay remain mandatory. Other source
traces, stale SSA, extra effects and unwitnessed guest layouts refuse without
publication. This does not implement arbitrary C strings or runtime C I/O.

### Six distinct guest-computed bytes (bounded binary witness)

The opt-in `--distinct-literal-six` bridge retains its original
current-profile `51 1c 4f 1d 50 1b` 15-step guest witness. A finite,
source-independent state-space solver now admits independently validated
nonhistorical six-effect streams with **either** zero or nonzero leading
bytes. The pinned Clang pipeline proves a complete two-trip C `while`
recurrence with branch-selected output triples and intervening local writes.
Its independent source oracle is `35 36 35 00 50 1b`, including an
interior NUL and repeated byte; actual normative VM execution emits that
stream in 19 steps for empty and nonempty input. The older zero-prefix
`00 51 22 1b 37 39` 23-step witness is also preserved.

Every admitted C effect remains bound to distinct source/SSA identities.
The compiler re-admits typed/MCTR and graphical source, validates safe
relocated guest data writes and exact output bytes in the normative VM,
and publishes no artifact if any stage fails. The search is bounded, not a
proof that arbitrary output sequences are synthesizable. C branches and
state are evaluated at compile time, not executed as guest control flow.

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

### Source-independent forty-one-byte literal proof

`encode_distinct_literal_forty_one` accepts exactly forty-one distinct
source-ordered `u8` constant/output SSA pairs and a void return, under
the current-profile canonical ternary wire contract. An independent real
VM witness proves forty-one guest-computed bytes in ninety-seven steps
with disjoint data writes, zero input consumption and exact output.
All other values, output counts, SSA effects and profiles reject. This
does not enable C source admission or arbitrary byte materialization.

### Source-independent forty-two-byte literal proof

`encode_distinct_literal_forty_two` accepts exactly forty-two independently
materialized, distinct byte SSA values and output effects in the proven order.
The normative current-profile VM confirms 42 guest-computed bytes, 42
disjoint source-external memory writes and exactly 97 steps without input.
Forged effects, changed bytes, prior prefixes, and foreign profiles refuse.
This is a finite bridge, not arbitrary byte-stream compilation.

### Source-independent forty-three-byte literal bridge

`encode_distinct_literal_forty_three` accepts only the exact 43 guest-
computed output bytes from the independently replayed 100-step
`ProfileMachine` witness. Ten reached no-ops place the relocation;
two internal no-ops adjust the data-read addresses, and four rotations
combine with 39 crazy writes. Ternary SSA effects, distinct data
writes, current-profile identity, exact output and zero input consumption
are independently verified before layout admission. Changed bytes,
forged effects or a different target profile fail closed. This does not
yet admit source C or arbitrary 43-byte output streams.

### Source-independent forty-four-byte literal bridge

`encode_distinct_literal_forty_four` accepts exactly 44 ordered ternary
constant/output pairs and a void return. Eleven leading no-ops place data
beyond the 103-cell source; two internal no-ops and six rotations yield
44 distinct guest-computed bytes from disjoint real VM writes. Canonical
current-profile identity, SSA wiring, exact byte order, zero input and
normative termination must all agree. Other outputs and forged effects
fail closed; source-C compilation is a separate admission boundary.

### Source-independent forty-five-byte literal bridge

`encode_distinct_literal_forty_five` admits the exact 45 distinct binary
bytes already proven by `guest_forty_five_distinct_literal_witness`. Eleven
leading no-ops, one internal no-op before byte 21, one trailing no-op, and
six data rotations produce 45 distinct guest writes outside the 105-cell
source. Canonical current-profile identity, pairwise SSA wiring, exact output,
zero input consumption, and real VM termination must all agree. Other byte
orders, changed values, SSA aliases, and foreign profiles reject; this does
not admit general C source compilation.

### Source-independent forty-six-byte literal bridge

`encode_distinct_literal_forty_six` admits exactly 46 ordered ternary
constant/output SSA pairs matching the 46 distinct binary bytes independently
computed by `guest_forty_six_distinct_literal_witness`, including `0x00` and
`0xff`. Ten leading no-ops, two internal pads before output indices 11 and
33, and six rotations relocate disjoint data writes beyond the 106-cell
source. Current-profile identity, exact SSA order, zero input consumption and
real VM termination must agree before the layout is returned. Foreign
profiles, altered constants and forged effects reject; this is not generic
byte-string lowering or C source admission.

### Source-independent forty-seven-byte literal bridge

`encode_distinct_literal_forty_seven` admits only the exact 47 source-ordered
ternary constant/output SSA pairs whose guest bytes are independently proven
by `guest_forty_seven_distinct_literal_witness`. Sixteen leading no-ops,
six interleaved no-ops and five rotations compute 47 distinct bytes through
47 disjoint data writes outside the 118-cell source. Canonical current-profile
identity, SSA binding, exact guest output, zero input consumption and VM
termination are required. Changed constants, forged effects and foreign
profiles reject; this is neither arbitrary byte-string lowering nor C source
admission.

### Source-independent forty-eight-byte literal bridge

`encode_distinct_literal_forty_eight` admits exactly 48 source-ordered
ternary `u8` constant/output SSA pairs whose values match the independently
verified `guest_forty_eight_distinct_literal_witness`. Thirteen leading
no-ops, ten interleaved no-ops and four rotations produce 48 distinct bytes
from disjoint guest data writes beyond 121 source cells. The exact current
profile, SSA binding, input independence and 121-step normative VM execution
must agree. Changed bytes, forged effects, short prefixes and foreign profiles
reject. This is a finite proof, not C-source admission or arbitrary output.

### Expanded loader-valid source scratch and six-bit recurrence

The variable source-scratch search likewise no longer equates the
shortest completed byte path with a verified guest. It tries up to four
deterministic complete path candidates when positional encoding, write
footprint or VM replay refuses an earlier path. Two retry/cap tests and
all real source-scratch guest witnesses pass, including twelve masked
Fibonacci bytes. The variable-byte proposal grammar and separate guest
semantic checks are unchanged. A later source-phase completion can be
missed when all four checks are spent on the shortest source lengths. The
same bounded solver now checks the three shortest completions and reserves
the fourth check for its longest completed source geometry. An independent
positional encoding and normative guest VM run verify that the later
zero-byte-pair candidate really emits both bytes. Rejected proposals still
never publish guest output; this changes sampling, not the four-check cap.

Forward-jump source-scratch search now checks completed output paths as
untrusted proposals instead of halting after the first complete accumulator
state. A rejected positional encoder, source-write check or real VM replay
allows subsequent paths or later source lengths, with at most four
completion attempts per source geometry. Red-first callback tests establish
rejected-first/accepted-next and the all-rejected cap; existing Fibonacci
source-scratch guests still execute under normative VM verification. This
recovers bounded proposal coverage, not arbitrary stream synthesis.

The bounded forward-jump source-scratch proposal now retains predecessor
links instead of copying full candidate paths. Its skipped-data operands
include both the canonical input and jump graphical code cells, in addition
to the six reached opcodes, selected once per address-sensitive decoder
phase. Those skipped cells are data, never executed: independent positional
layout admission and real VM replay decide whether the resulting guest is
valid. `tests/compiler/bridge/source_scratch.rs` checks both kinds of skipped
words have genuine arithmetic effects without consuming input.

`tests/test_compound_c_pipeline.py` independently validates twelve full
Fibonacci C loop/conditional effects under a six-bit mask, yielding
`02 19 1f 08 17 0f 22 2d 03 10 33 23` with real guest execution on empty
and nonempty input. Division-by-zero mutation refuses publication. The
unmasked original C stream still refuses at layout; finite source-scratch
search is neither a complete C runtime nor arbitrary output synthesis.

The same proposal grammar now varies the source-proven jump phase across the
first four code positions rather than requiring an immediate jump. Prefix
positions are real reached instructions: they may be no-ops or, when the
independent effect trace begins with zero bytes, actual `OutputByte` effects
before the jump. The remaining source-scratch operands start at the shifted
D pointer; the jump's exact graphical encoding, encryption target, and every
later source write are checked by the layout verifier and normative VM.
This remains a search capped at five pre-output no-op/arithmetic
instructions per effect, not arbitrary byte synthesis. The complete
twelve-byte masked Fibonacci recurrence also
has a delayed-jump witness (47 guest steps), and a two-NUL-prefixed
recurrence has a separate verified guest witness under EOF and binary stdin.
An unmasked `02 59 5f` prefix remains unsupported by this grammar.

For twelve distinct source-proven bytes, the bridge now tries the bounded
forward-jump scratch grammar before the costlier relocated-tail proposals.
When scratch synthesis succeeds, the same independent layout and two-input
normative VM checks still govern publication. If it cannot prove the byte
sequence, the existing straight-write and bounded short-layout grammars remain
available in their original order. The complete masked twelve-step C
Fibonacci source continues to pass the real compiler and guest-VM pipeline;
this search ordering does not admit the unmasked original or dynamic C loops.

A separate deterministic scalar regression enumerates the current
source-scratch grammar after the original unmasked Fibonacci prefix
`02 59`. It considers all eight loader-valid graphical skipped words and
up to twelve no-op/crazy/rotate choices per byte, without collapsing full
accumulator words to their low byte. Exactly 205 distinct third-byte values
are reachable in that grammar; `0x5f` is not one of them. The earlier
source-scratch two-byte witness still runs on the actual normative VM.
This bounds one positional graphical-operand grammar only: guest-written
non-graphical operands, more general data relocation and full C runtime
lowering remain separate work. No new source or arbitrary guest byte stream
is admitted on the strength of the scalar reachability test alone.

### Exploratory forward data relocation in source scratch

A test-only bounded proposal now permits one forward data-pointer relocation
inside graphical scratch skipped by a source-proven jump. It tracks both
accumulator words and data-pointer phases, never revisits guest-written
operands, and independently admits the positional source plus two normative
VM executions. A three-byte `02 59 5d` witness executes genuine guest
arithmetic, a scratch-pointer relocation, and three ordered outputs under
EOF and binary stdin. This is a new guest execution geometry, not arbitrary
C byte-stream synthesis or a production lowering fallback.

The original unmasked Fibonacci third byte `5f` remains unproved.
The exploratory search is deliberately not called by the production
compiler: its bounded negative-case search cost is not yet acceptable.
Follow-up work needs a faster admissible search strategy and a complete-C
end-to-end demonstration before adopting this grammar.

### Bounded search beyond the one-byte witness tables

When the existing positional one-byte witness selector has no entry, the
current-profile single-output bridge may instead search a bounded grammar of
source-encoded no-ops, one data relocation, and one or two genuine `p`/`*`
writes before `<` and halt. Candidate byte previews are not authority: the
independent layout checker must re-decode the complete graphical source,
prove data-write placement, and the normative VM must emit the requested
byte under empty and nonempty input.

A source-C `putchar(64)` previously refused at layout, and now emits `0x40`
in seven VM steps. The same search has independently realized `0xff` in 41
steps. The deeper single-output fallback also searches three disjoint guest
arithmetic writes with bounded positional strides. A complete three-iteration
unsigned C recurrence with multiplication, shifts, a conditional, state
transfers, and final XOR now produces byte `0x7f`, which the older one- and
two-write search refused. Candidate previews only reject proposals;
independent graphical-layout admission and normative VM replay on empty and
nonempty input decide acceptance. The deeper grammar is restricted to a
single output effect so existing repeated-output
search costs are unchanged. This remains finite candidate search, not
arbitrary byte synthesis; the twelve-byte Fibonacci trace is unsupported.
Existing seed-selected witnesses are unchanged.


### Verified scratch-written data relocation

The source-scratch regression composes a verified two-byte Fibonacci
prefix with two real guest `j` instructions after a graphical scratch
`*` write. The first relocation returns to the earlier, modified
source cell; the second uses its newly rotated 15-trit value to select
loader-expanded guest memory, well beyond the graphical source. The
normative VM emits `02 59 0b` and halts in 95 steps under empty and binary
stdin, with zero input consumption. The final byte is a genuine guest
accumulator output, not a host-synthesized suffix. This is a test-only
linker geometry witness, not general C-to-guest translation. The original
unmasked Fibonacci third byte `5f` and full twelve-byte stream still lack
an admitted layout.

### Expanded-memory arithmetic after scratch-written relocation

The source-scratch relocation regression now also proves two distinct writes
**after** the modified graphical word relocates D into loader-expanded memory.
The actual guest first emits the first two independently derived Fibonacci C
bytes `02 59`, rotates an earlier scratch operand, reads that changed word
through a second live `j`, and then executes `p`, output, `*`, output on two
previously untouched expanded-memory words. Independent loader-word arithmetic
predicts `02 59 b9 b6`; the normative VM verifies the four exact bytes and
98 executed instructions under empty and binary stdin. The two expanded writes
are separate from each other and from the earlier scratch write, with no input
consumption. This test-only linker geometry does not enable a production
C-to-Malbolge fallback or resolve the unmasked third Fibonacci byte `5f`.

### Finite expanded-tail reachability after a written source relocation

The source-scratch guest regression now enumerates a bounded *negative*
search for the unmasked Fibonacci third byte `0x5f`. After two verified
source output effects and a guest-written data relocation into loader-expanded
memory, the scalar search permits up to twelve further operations from
`o`, `p`, `*`, and `j`, including at most two more `j` relocations. Four
different terminal opcodes before halt vary the loader recurrence seed.
All intermediate accumulator values retain their full 15-trit width.

No state in that fresh-expanded-word grammar has low byte `0x5f`. Its
exploration can include paths that would be rejected by the positional
layout checker, so the negative result applies only to paths that read
untouched expanded words, not to guest-written operand revisits or alternate
source-scratch geometry. The independently admitted `02 59 b9 b6` guest
still executes under EOF and binary input. This search is test-only; it
does not introduce a compiler fallback or prove arbitrary byte synthesis.

### Exhaustive monotone source-scratch operand graph

`tests/compiler/bridge/source_scratch.rs` now enumerates exact accumulator
and output-prefix state for a phase-zero forward code jump with every possible
loader-valid graphical operand and arbitrarily many **forward-only** data
relocations. It explores 96,732 distinct phase/accumulator/output-prefix
states without reaching the original Fibonacci `02 59 5f` prefix. Its positive
control `02 59 5d` has a real 109-cell, eleven-step VM guest witness.
This negative result covers only fresh source operands: backward or
written-word revisits, alternate jump phases and expanded loader memory may
still enable the original byte stream. The experiment is a test-time design
constraint, not an accepted general-purpose synthesis algorithm.


### Revisit of guest-written graphical scratch (2026-11-11)

The original complete unsigned Fibonacci C program requires output
`02 59 5f 08 57 4f 22 6d 03 90 b3 23`. The first three bytes now have an
independently admitted **real guest** under the current VM. The test
`tests/compiler/bridge/unmasked_fibonacci.rs` starts with a source-scratch
witness for `02 59`, advances D through reached no-ops, and rotates a
previously skipped graphical word at address 67. A real `j` reads the
unmodified graphical word at 68 and redirects D to the just-written word
at 67. A second `*` then reads this full-width, guest-modified value, and
four real `p` operations yield the previously unreachable byte `0x5f`.

The completed 174-cell source halts after 76 executed instructions and emits
`02 59 5f`, with no input consumption, under both EOF and binary stdin.
Its C-byte oracle comes from the complete unsigned recurrence, independently
of the guest path; the ordinary layout checker re-encodes all source cells,
proves the actual write and relocation positions, and the normative VM runs
the resulting source. This shows why the earlier negative graphical-only and
untouched-expanded-word searches were intentionally **grammar bounded**:
revisiting a guest-written graphical operand adds genuine state beyond both.

This is still a **test-only** evidence witness, not production automatic
synthesis, complete twelve-byte original Fibonacci compilation, or general
C guest-side branches. The remaining nine original bytes and a bounded
automatic discovery strategy remain open.

### Search proposals starting at the first expanded word (2026-11-11)

The byte-stream state-space, straight-write and multi-relocation preview
filters now use the same post-`j` data-pointer boundary as the independent
layout checker. A graphical operand at `source_length - 1` increments D to
`source_length`, which is already a loader-expanded word. Earlier preview
filters compared the raw operand against the source length and discarded
that safe geometry before verification.

A red-first regression constructs a real 34-cell guest with the `j` at
position seven encoded as `33`, then performs source-independent arithmetic
using D=34. An independent recurrence for the first expanded word predicts
the output byte; the full position-encoded proposal passes independent
layout admission and two normative guest VM replays. The same operand with
a 35-cell source must be rejected as a source-overlap write. The original
unmasked Fibonacci C experiment was retried and still refuses at
`Layout(UnsupportedEffectTrace)`, so this corrects candidate coverage only;
it is not a general synthesis or runtime-control capability.

### First loader-expanded relocation word (2026-11-11)

The three-write, four-write triple and four-write quad preview filters now
compare the *post-`j`* D pointer with the complete source length. An operand
of 33 increments to D=34, the first loader-expanded word of a 34-cell guest.
Previously the previews rejected this safe boundary because the raw operand
was smaller than 34; the independent linear-layout admission had the same
overly strict guard and now checks the actual post-increment destination.

A 34-cell four-write guest emits `3f 2c 12` under empty and binary stdin
in the current-profile normative VM. The independent layout re-admits all
source cells and four distinct expanded-memory writes at 36, 40, 47, 57.
Both current and historical VMs check the boundary against a separate scalar
loader-recurrence oracle. Growing the same source so relocation points into
pending code still rejects. This work corrects a safe guest layout boundary;
it does not compile the original unmasked twelve-byte C Fibonacci program
or implement dynamic guest control.


### Six independent loader-data regions (2026-11-11)

The bounded twelve-effect byte-stream proposer now accepts **six** live
`j` data relocations, not only five. This is a distinct source geometry:
each relocation reads an untouched loader-expanded operand and changes where
the next real `p` arithmetic effect reads and writes memory. The proposer
does not select relocation destinations or output bytes on the host; the
normative guest performs every data operation.

A source-independent 32-cell positional guest with one prefix no-op,
six relocations, twelve `p`/output pairs and a final halt emits
`3e 0b 4a 29 5c 32 53 50 3d 0a 49 31`. The original positional
encoder and independent bridge admission prove all twelve writes are distinct
and outside the code, while the normative VM executes the complete stream
under EOF and binary input. The six-region proposer recovers the exact
source, and the production twelve-byte path independently publishes an
equivalent verified program. A mismatched output byte refuses publication.

The six-region fallback runs only for twelve-effect streams, after prior
bounded proposal grammars. This is source-independent guest byte synthesis,
not general runtime C arithmetic, arbitrary relocations or a solution to
the unmasked Fibonacci stream `02 59 5f ...`.

### Necessary instruction bound for short output streams (2026-11-13)

A five-output variant of the full C Fibonacci-style recurrence with seeds
`a = 2U` and `b = 3U` reached the real guest layout stage but did not
produce an artifact within the bounded experiment. The search previously
used its necessary output/write instruction bound only for eight or more
pending effects, leaving impossible shorter frontiers unfiltered.

Every pending output needs a guest `<` instruction. Each transition to a
different byte needs at least one real `p` or `*` accumulator write; no-op
and output cannot change the accumulator. The same necessary bound now
filters all stream lengths without discarding exact accumulator values or
weakening the independent layout and normative-VM verification gate.
Red-first short-stream tests prove insufficient body capacity rejects and
exactly sufficient repeated outputs remain. This change improves proposal
pruning; it does not prove completeness, runtime C arithmetic or general
source-independent byte-stream synthesis. The seeded C variant remains
unwitnessed under the experiment budget.

### Short-stream source-geometry capacity preflight (2026-11-13)

The same necessary output/write bound now applies before source-tail
reconstruction for every prefix geometry, including streams shorter than
eight effects. Both the maximal initial-zero prefix and each actual
prefix-output choice must leave enough body instruction cells for remaining
outputs and byte transitions. This only rejects mathematically insufficient
source geometries; it does not change the minimum searched source length,
relocation phases or verified candidate ordering. The independently decoded
five-byte nonfixture guest with a leading zero and the historical five-byte
canonical bridge still execute and match the normative VM.

### Fourth-loader-cell dense-frontier continuation (2026-11-14)

A bounded eight-output guest-search experiment exposed a distinct false
negative under the 16,384-state frontier threshold. All 8,192 candidate
accumulator words in the seed share low byte `3`. After one output,
the non-extreme full word `259` can reach byte `1` through two genuine
crazy writes with future loader words `[0, 0, 0, 2]`; the previous
three-cell beam lookahead discarded it in the dense case even though
an exact sparse frontier kept it.

The beam now considers a fourth *proven* future word, retaining up to two
additional full-word representatives per output-progress/byte class.
Missing future words never become guessed zero operands, and the extra
lookahead still reserves one instruction for the pending output. The
red-first regression checks the dense survivor, the independent scalar
crazy result, the changed-fourth-word negative case and insufficient
instruction capacity. Focused prior beam regressions retain their earlier
behavior. This only widens bounded candidate search; source encoding,
independent layout admission and normative VM replay remain the sole
publication gate. General byte-stream synthesis and dynamic C guest
arithmetic/control are still unsupported.

### Relocation-aware dense-beam future operands (2026-11-14)

The bounded multi-region proposal previously predicted all future crazy
operands from consecutive loader addresses in the current region. A later
real `j` relocates D, so these hints could favor the wrong high-word
accumulator and discard a viable continuation when the frontier exceeded
16,384 states. The proposal now follows the independently derived sequence
of data addresses across each live relocation, skipping `j` instruction
positions; absent future operands do not become invented reachable paths.

A red-first focused regression exercises the actual two-relocation geometry,
confirms the second region's source-independent loader word rather than the
old region's sequential word, and checks that the remaining future operand
slots are absent. Existing repeated-relocation guest and normative-VM tests
remain the independent acceptance boundary. This repairs a bounded search
heuristic, not general synthesis, dynamic C state, or a semantic proof of
search completeness.

### Unknown loader words in bounded beam lookahead (2026-11-14)

A red-first dense-frontier regression found that split-region search converted
missing first, second or third future loader operands into the integer zero.
For a middle accumulator word of `259`, that fabricated a `p(0, A)` path to
byte `53`, or a second `p(0, A)` after a real operand `2` to byte `255`.
These are valid arithmetic continuations only when the corresponding loader
word actually exists and equals zero.

The proposal now carries optional loader operands for all four future cells,
stopping lookahead at the first unknown cell. Ordinary single-relocation,
repeated-relocation and source-scratch proposals use the same boundary; a
missing lookahead value is no longer a reason to reject an otherwise valid
current search position. Real zero operands still retain the necessary
high-word continuations, as tested by a positive two-write control. This
corrects heuristic retention only: independently admitted positional code,
write-disjointness and normative VM execution still govern publication.
The checkout used for this regression lacked the pinned C frontend binary,
so it does not establish new end-to-end C compilation or retire P0.

### Short dense guest-search frontiers (2026-11-14)

A red-first seven-output search case exceeded the 16,384-state frontier
budget even though the existing high-word beam could retain its real next-byte
continuation. The old beam gate applied only to streams of eight or more
outputs, so this shorter shape abandoned the whole geometry without trying
a possible guest continuation. Dense frontiers now use the same
bounded, full-word-aware beam at any output count; sparse frontiers remain
exact. The test preserves accumulator `259` through an actual `p(0, 259)`
change from byte `3` to `53`, the subsequent output step, and an unknown-word
negative control. This is a search-budget repair, not a new C language
feature, a promise of search completeness, or a relaxation of the positional
layout and normative VM acceptance gates. The pinned frontend remains absent
from this checkout, so no new end-to-end C result is asserted.

### Balanced dense source-revisit frontiers (2026-11-14)

The source-revisit continuation search previously spent its entire
16,384-state cap on the highest output-progress counts. A dense six-count
regression showed that this could discard *every* less advanced path even
when its full accumulator word might be needed for later crazy arithmetic.
The bounded continuation now reserves minimum and maximum full-word states
per output-progress/low-byte group before filling remaining capacity with
advanced states. Small frontiers remain exact and every recovered guest
still requires independent positional admission and normative VM replay.

The focused beam regression passes, as does the unchanged independently
verified three- and four-byte Fibonacci source-scratch guests in both
bridge entrypoints. This run does not establish a complete twelve-byte
unmasked Fibonacci guest, any new end-to-end C compile, or completeness of
bounded proposal search.

### Fair progress quotas and full-stream typed evidence (2026-11-14)

The source-revisit beam kept two accumulator extremes per output-progress
and low-byte group, but then filled its entire 16,384-state budget from the
most advanced counts. A red-first six-count regression showed that this
removed the intermediate full word `259` at early counts even though a real
`p(0, 259)` reaches output byte `53`. The new retention pass divides room
among all active progress counts before advanced-first redistribution. Its
cap, exact sparse search and full-word identities remain unchanged.

An independent baseline comparison found that the pre-existing full-stream
source-revisit search *already* generates the original unsigned Fibonacci
bytes `02 59 5f 08 57 4f 22 6d 03 90 b3 23`. Both old and new search
passed the existing twelve-byte normative VM replay with a real guest-written
source revisit and two data relocations. A canonical typed-IR publisher also
admits this trace, exposing an obsolete negative expectation in its test.
These results are bounded guest layout/typed-lowering evidence, **not** a
new pinned-Clang C-to-VM compilation or guest-side C arithmetic. The pinned
C frontend was absent in this checkout, so full source-C parity and P0
acceptance remain unverified.

### Middle full-word diversity across byte classes (2026-11-14)

A red-first six-progress frontier with all 256 low-byte classes exposed
another bounded-revisit search loss. The old per-progress quota protected
each class's smallest and largest full accumulator word, but filled its
remaining space with low numerical words. It discarded `8195`, whose real
`p(0, 8195)` transition emits byte `93`, unlike the same-low-byte extremes
`3` (byte `50`) and `16387` (byte `223`).

Each active progress/low-byte class now also reserves its available
full-word representative nearest the numerical midpoint before the
per-progress quota and advanced-first fallback. This stays under the same
16,384-state cap: at most nine progress counts and 256 low bytes create
6,912 protected candidates, including all three representatives. Sparse
frontiers remain exact. The red-first boundary test and the existing full
twelve-byte Fibonacci guest and canonical typed publisher pass normative
VM replay. This does not establish complete search, guest C arithmetic,
or pinned-Clang C-to-VM acceptance; the exact frontend binary was absent.

### Late positional completion with four verifier checks (2026-11-14)

Complete output counts before the final body cell are not necessarily valid
positional encodings. Previously the linear and multi-relocation searches
consumed every one of their four verification slots on early candidates,
missing a different source phase at the last body cell. Red-first one- and
two-relocation callback tests now pass after reserving the final slot for
the latest complete phase, preferring newly emitted output over no-op
padding at equal phase. All three earlier checks remain available for short
candidates. A real 16-step relocated guest emits one zero byte from its last
body cell and is independently replayed on empty and binary stdin. The
search recovers the same encoded source without enlarging the four-check
budget or relaxing source-write, positional or VM validation. The full
conditional Fibonacci C source remains blocked by missing pinned LLVM 22;
this is not guest runtime C arithmetic or general byte-stream synthesis.

### Verified split-relocation completion retries (2026-11-14)

The multi-relocation proposal previously returned the first full output path
following its last live `j`. Positional encoding or independent VM replay could
reject that proposal even when later accumulator states or source-cell padding
in the same geometry would succeed. The two-, three-, and four-relocation
production paths now invoke independent admission **inside** the search,
continuing after rejection with at most four checks per geometry. A red-first
split-geometry regression verifies first-rejected/later-accepted candidates,
distinct two-relocation paths, and the four-rejection cap. Existing real guest
relocation witnesses remain the authority for emitted output. The pinned C
frontend is absent, and this does not prove arbitrary stream synthesis.

### Independently verified completion retries (2026-11-14)

A complete byte count in the straight-line candidate map is not yet a
verified program. The former search returned its first complete path and
discarded the remaining source geometry if independent admission failed.
The new callback checks each completed proposal, trying later candidates
under a fixed four-completion budget. Rejected candidates cannot publish.

A two-entrypoint regression demonstrates rejection followed by acceptance
and exhaustion after exactly four unsuccessful attempts. The previously
verified no-op terminal guest still executes under the normative VM. The
pinned Clang source frontend remains unavailable and P0 is pending.

### Completed source-revisit paths survive dense pruning (2026-11-14)

The source-revisit search formerly omitted exact complete-output states from
its dense-beam selection. If the first candidate halt failed positional
admission, the next source-cell iteration could no longer retry the same
accumulator with added no-op padding. A red-first 28,672-candidate case now
retains completed full-width words within the unchanged 16,384-state cap and
proves their predecessor links remain live through a second search layer.

The original complete twelve-byte Fibonacci guest passes normative VM
replay with and without binary input in both bridge entrypoints. The pinned
Clang C frontend remains absent, and this correction does not provide
general C runtime arithmetic, control flow, or arbitrary byte synthesis.

### Retained-only source-revisit histories (2026-11-14)

The source-revisit continuation previously appended a reconstruction record
for every distinct proposed full-word state before beam pruning. A dense
frontier could discard thousands of those records per source cell but still
retain their memory, despite the intended 16,384-state frontier cap. The
search now keeps candidate links temporary and appends permanent predecessor
records only for surviving states. Full-word keys, source-memory constraints,
beam ordering, sparse exact frontiers and independent layout/VM proof remain
unchanged.

A two-layer regression with 24,576 first-layer candidates checks the exact
16,384-record retention and all second-layer parent pointers. The complete
twelve-output original Fibonacci byte stream and canonical typed publisher
still replay correctly on the normative VM. Missing pinned native Clang
prevents a full source-C pipeline claim; this change does not implement guest
C arithmetic, runtime control flow, or arbitrary byte-stream synthesis.

### Bounded dense guest-output beams (2026-11-14)

The source-independent candidate search can retain more than 16,384 states
when each progress/low-byte group protects its own full-word reachability
hints. A red-first 12-progress, 256-byte-class frontier exposed 16,442
survivors after the original pruning pass. A second balanced pass selects at
most 16,384 candidates, keeps each active output count represented, and
stores predecessor records only for survivors. Sparse frontiers are unchanged.
The output candidate still requires independent positional encoding, source
write checks and actual VM replay before acceptance. This is not runtime C
arithmetic or a general byte-stream synthesizer.
