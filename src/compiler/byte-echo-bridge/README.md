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

Both APIs revalidate the whole canonical ternary program, match the selected
profile, and delegate source encoding/admission to `malbolge-layout`. They
emit the actual source code; no host callback performs guest byte I/O.

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
