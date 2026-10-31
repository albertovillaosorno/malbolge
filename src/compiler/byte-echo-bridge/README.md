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

### Verified initial-zero guest output

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
`MaterializeU8(value)`, one to eight `ByteOutput`s of that SSA
identity, and `ReturnVoid`. For one output, it admits only these
current-profile nonzero bytes: `4, 5, 6, 9, 10, 11, 18, 19, 20, 21, 22,
23, 251, 253`. For exactly two identical outputs, a **different** table
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

A profile-specific *proposed* no-op prefix precedes `j`, `*`, the actual
`<` outputs, and `v`. The canonical loader expands the complete graphical
source into guest memory. Changing the output count changes the positional
encoding and the loader-expanded data; therefore seeds are admitted per
exact output count, not reused across modes. The guest `*` rotates its real
data word into A, and the
guest outputs emit the unchanged accumulator. The independent layout checker
proves source/data separation and a fresh normative VM checks every emitted
byte, exact halt, and zero input consumption before accepting a source.
Other literals, zero/nine-or-more outputs, extra effects and foreign profiles
reject.
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

Six-, seven- and eight-output witnesses independently repeat the same bounded
`0..26` scan, with their own loader-expanded source. All 26 tested phases
for each count emit identical nonzero bytes and terminate without input.
The first successful witness per value yields 19 shortest prefixes for six
outputs, 18 for seven and 21 for eight. Reproduce the independent
optimized scans with:

```sh
cargo test --release --locked --test rotated_byte_constant_bridge \
  independently_rederive_six_output_rotation_witnesses -- --ignored
cargo test --release --locked --test rotated_byte_constant_bridge \
  independently_rederive_seven_output_rotation_witnesses -- --ignored
cargo test --release --locked --test rotated_byte_constant_bridge \
  independently_rederive_eight_output_rotation_witnesses -- --ignored
```

Default regressions enumerate all 256 byte values separately for four,
five, six, seven and eight same-SSA outputs. They require 24, 18, 19, 18
and 21 shortest prefixes respectively, rejecting 232, 238, 237, 238 and 235
other byte values per count. The canonical typed adapter, CLI publisher
and real guest runner verify successful and rejected count-specific cases.

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
