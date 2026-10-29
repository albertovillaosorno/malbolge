# Byte Echo Bridge

## Purpose

Prove one small executable end-to-end compiler slice without weakening the
canonical pre-layout ternary model or the independently admitted graphical
Malbolge encoder.

## Ownership

`composition/lib.rs` admits a one-function, value-free-return program with
one or more adjacent `ByteInput`/`ByteOutput` pairs, using the same SSA byte
identity in each pair. It revalidates the whole ternary program, matches the
canonical target profile, maps the pairs to contiguous raw input/output
instructions, and delegates source encoding and admission to `malbolge-layout`.

## Limits

The trace is equivalent **only on successful byte I/O**: every input must
provide a byte rather than EOF, and every output must succeed. The final void
return is process termination; guest calling-convention state, status codes,
EOF/error semantics, arithmetic, nonadjacent dataflow, globals, and multiple
functions are not realized. Rejections are explicit, not fallback emulation.

## Validation

`cargo test --locked --test byte_echo_bridge` executes the generated source in
the normative current-profile VM and checks the exact input/output trace, as
well as profile drift, oversized trace admission and unsupported-effect
rejection. An independently admitted canonical typed-IR byte-I/O function
round-trips through typed-IR and ternary wire formats before executing on the VM. This capability is a
bounded integration witness, not the full C-to-Malbolge backend.
