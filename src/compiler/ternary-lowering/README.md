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
exact `i32` constants/returns, `i32` bitwise AND, `i32`-to-`u8` truncation, and
deterministic typed-IR `ByteInput`/`ByteOutput` effects. Exact 32-bit bit
patterns become fixed-width 21-trit scalars while source, ABI, typed-IR version,
source digest, and target-profile provenance are preserved. Byte effects remain
successful `u8` semantics.

Canonical `malbolge-ternary-ir-v1` bytes now serialize that pre-layout
`TernaryProgram` only after independent stage validation. The `MCTR` version-one
wire uses fixed little-endian integers, length-prefixed UTF-8 identities,
explicit
operation tags, exact source spans, and 21 one-byte trits per `i32` scalar.
Restoration rejects malformed, truncated, unknown-tag, noncanonical, or
semantic-invalid state before returning a program.

A separate pure runtime-helper port admits only
`malbolge_guest_decode_input_word` and `malbolge_guest_output_byte` under the
current profile. It lowers them to declarative target recipes: input accepts raw
words `0..255` or the profile EOF word and carries exact valid/invalid statuses,
while output carries the exact low-eight-bit mask. These recipes never evaluate
a guest value on the host. Input helper realization now expands that recipe into
ordered null-pointer, byte, EOF, and invalid-word exits with exact result and
runtime-status publication; output realization retains its exact low-byte mask.

A separate frame-helper boundary now admits the exact
`malbolge_guest_frame_validate`, `malbolge_guest_frame_encode`, and
`malbolge_guest_frame_decode` identities under `malbolge-c32-v1` and
`malbolge-guest-runtime-v1` authority. Validation expands to ordered
null/extent/alignment/argument/flags/success exits. Encode/decode additionally
bind all eight fixed little-endian field offsets and defer caller-visible wire
or frame publication until validation succeeds, without reading guest values on
the host.

Public `getchar`/`putchar` planning now composes those helper recipes with the
raw intrinsic semantics in the exact order implemented by guest stdio: input
intrinsic then decoder for `getchar`, helper then output intrinsic for
`putchar`. The raw intrinsic step can now be rebound through the canonical
target-profile projection to the selected machine opcode while preserving the
helper recipe, order, and return semantics. Machine wrapper plans also carry
the explicit helper execution plan.

A follow-on wrapper-control-flow step makes `getchar` initialization/status
guarding and `putchar` helper/I/O/return order explicit without assigning branch
addresses. The canonical libc manifest remains unchanged and still marks both
routines contracted-unavailable pending source-cell placement and complete
target layout.

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
bind-call encoding, typed-IR external-call binding, wrapper branch-address and
source-cell placement, global layout, target serialization, and complete
Malbolge emission remain open.
