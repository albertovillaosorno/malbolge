# Ternary Lowering

## Purpose

Own deterministic lowering from validated typed compiler semantics into a
pre-layout ternary representation suited to later Malbolge layout and encoding.

## Ownership

This boundary is owned by `function:ternary-lowering`.

## Prohibitions

It must not parse C, import typed-IR implementation types, choose final target
addresses, encode Malbolge source, or substitute host computation for guest
semantics.

## Navigation

- `port-inbound/`: narrow semantic projection accepted from validated typed IR.
- `domain/`: deterministic pre-layout ternary values and source provenance.
- `application/`: fail-closed semantic lowering into target operations.
- `composition/`: canonical module topology for compiler assembly and tests.

## Status

The executable slice lowers admitted no-argument, single-block functions using
exact `i32` constants/returns plus deterministic typed-IR `ByteInput` and
`ByteOutput` effects. Exact 32-bit bit patterns become fixed-width 21-trit
scalars while source, ABI, typed-IR version, source digest, and target-profile
provenance are preserved. Byte effects remain successful `u8` semantics.

A separate runtime-intrinsic port admits only the exact
`malbolge_guest_intrinsic_input_word` and
`malbolge_guest_intrinsic_output_byte` declarations under `malbolge-2026`,
lowering them to distinct raw `InputWord` and `OutputByte` pre-layout semantics.
A target-profile port then copies canonical I/O instruction bytes and EOF state
from the admitted profile descriptor and realizes those operations without
hardcoded opcode characters. An instruction-decoder port lets lowering invert
the canonical VM decode relation without copying XLAT1, producing one unique
graphical source cell for an already-selected code position.

Startup planning now accepts only a layout-resolved guest heap extent, validates
the canonical ABI pointer encoding plus runtime heap geometry, and emits exactly
one `BindHeap` action before `EnterUserCode` while retaining the exact
`malbolge_guest_runtime_bind_heap` identity. Arena placement, executable
bind-call
encoding, C EOF/helper lowering, global layout, target serialization, and
complete Malbolge emission remain open.
