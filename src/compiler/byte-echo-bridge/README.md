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
