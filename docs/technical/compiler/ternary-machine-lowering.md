# Ternary machine lowering

## Status

Active

## Purpose

Lower typed C IR into a compact ternary virtual-machine representation suited to
Malbolge instead of translating C operations directly instruction by
instruction.

## Scope

This document governs the following declared TODO scope:

- `compiler/`
- `src/`
- `tests/compiler/`
- `tests/ternary_lowering.rs`

## Current Behavior

### Implemented Initial Model

`src/compiler/ternary-lowering/` now owns the first executable pre-layout target
model. Its inbound port accepts a copied semantic projection from already
validated typed IR rather than importing the upstream implementation type. The
application lowerer currently admits no-argument functions containing one
entry block, no phi nodes, exact `i32` constant materialization/return, `i32`
bitwise AND, `i32`-to-`u8` truncation, and typed-IR `ByteInput`/`ByteOutput`
effects. Other admitted typed-IR shapes fail explicitly.

Exact 32-bit constant bit patterns are converted to a fixed 21-trit,
least-significant-trit-first scalar. Twenty trits are insufficient for every
`u32` bit pattern, while 21 trits cover the complete 32-bit representation
domain. The pre-layout program retains upstream function/value IDs plus exact
source spans, source digest, ABI identity, typed-IR version, and target-profile
identity.

Typed `ByteInput`/`ByteOutput` lower in source order to explicit target
byte-effect operations with SSA type/order validation. These operations preserve
the typed IR's successful `u8` semantics and do not impersonate the raw profile
input word or its EOF case.

The same SSA boundary now lowers typed `i32` bitwise AND and validated
`i32`-to-`u8` truncation. Together with constant materialization and
`ByteOutput`, these operations express the exact low-eight-bit transformation
used by `malbolge_guest_output_byte` without evaluating guest values on the
host.
Direct calls to that runtime helper are not yet recognized by this stage.

A separate pure runtime-helper port now admits exactly
`malbolge_guest_decode_input_word` and `malbolge_guest_output_byte` under the
reviewed current profile. It lowers those identities to declarative recipes
rather than host-evaluated values: input records the `0..255` byte domain, the
profile-projected EOF word, exact `EOF == -1` bits, and valid/invalid runtime
statuses; output records the low-eight-bit mask. An EOF projection overlapping
the byte domain fails closed.

The current typed IR cannot yet represent declaration-only external helper
callees: direct `Call` targets resolve only to module-local functions, and every
function must own a reachable entry block. Therefore this helper recipe is
semantic lowering evidence, while direct helper-call integration and executable
branch/status publication remain open.

A public byte-stream wrapper planner composes those helper recipes with the raw
intrinsic operations using the checked-in guest stdio order. `getchar` plans
`InputWord` before decode and returns decoded `i32` byte-or-EOF semantics;
`putchar` plans low-byte reduction before `OutputByte` and returns the emitted
byte widened to `i32`. A follow-on realization step revalidates the complete
wrapper plan and replaces only the raw intrinsic with the profile-bound
`MachineIoOperation`; forged plan order and malformed/colliding profile
projections fail closed. The canonical libc manifest remains unchanged and both
routines stay `contracted_unavailable` until helper control flow and target
layout are executable.

The separate raw runtime-intrinsic port admits only
`malbolge_guest_intrinsic_input_word` and
`malbolge_guest_intrinsic_output_byte` under the exact `malbolge-2026` profile.
Those identities lower to distinct pre-layout `InputWord` and `OutputByte`
operations; `InputWord` explicitly includes the selected profile's EOF word.
Unknown intrinsic names or profile drift fail closed.

A separate target-profile projection copies the current descriptor's exact
profile ID, input/output instruction bytes, and EOF word. Runtime I/O
realization uses only that projection, producing profile-bound machine
operations
without hardcoded `/` or `<` characters; colliding projected input/output
instructions or profile drift fail closed.

For an already-selected code-pointer position, the target-cell encoder exhausts
graphical ASCII `33..126` through a canonical instruction-decoder port and
requires exactly one source cell whose VM decode equals the realized operation.
The compiler therefore does not copy XLAT1. Missing or ambiguous inverse
encodings fail closed.

A separate startup port accepts a heap extent only after another stage has
resolved its guest logical location. Startup planning validates the exact
`malbolge-c32-v1` object-pointer encoding, 16-byte arena alignment, aligned
capacity of at least 32 bytes, `u32` logical-address containment, exact
`malbolge-2026` profile identity, and exact
`malbolge_guest_runtime_bind_heap` symbol. The resulting plan contains exactly
one bind action followed by user entry, so later layout/linkage cannot silently
place allocation-capable user code before the required bind.

This is executable compiler lowering but not complete target code generation.
Global layout/address assignment, concrete heap-arena placement, executable
runtime-call encoding, complete source sequencing, typed-IR external-call
binding, executable helper branching/status publication, target serialization,
and complete Malbolge emission remain downstream work.

### Authoritative Inputs

The first implementation must consume existing identities without renaming or
reinterpreting them:

- canonical compiler state is `malbolge-typed-ir-v1` under ABI
  `malbolge-c32-v1`, preserving the module's exact source and target-profile
  provenance;
- guest-runtime semantics are versioned by `malbolge-guest-runtime-v1`, whose
  current reviewed target profile is `malbolge-2026`;
- compiler-generated startup must realize the one-shot
  `malbolge_guest_runtime_bind_heap` entry before allocation wrappers become
  available to user code;
- byte input and output must realize the exact declaration-only identities
  `malbolge_guest_intrinsic_input_word` and
  `malbolge_guest_intrinsic_output_byte`; and
- the guest-runtime contract's `host_fallback` value is `forbidden`, so none of
  these operations may be replaced by host callbacks in accepted lowering.

No ternary-stage serialization identity is defined yet. The current in-memory
model is deterministic but deliberately pre-serialization. A wire identity may
be introduced only together with concrete canonical encoding and round-trip or
normalized golden evidence; this document does not reserve an unimplemented
wire name.

## Invariants

- Every IR operation lowers to explicit ternary/runtime operations with defined
  pre/postconditions and no direct host implementation of guest computation.
- Guest-runtime semantic identities supplied by `guest-runtime-and-allocator`
  lower to executable ternary/Malbolge-oriented operations without host callback
  substitution.
- The stage has deterministic input/output form, rejects malformed or
  unsupported input explicitly, and preserves source/profile provenance needed
  downstream.

## Failure Behavior

Malformed inbound projection identity, retained globals/proof obligations,
non-`i32` or malformed constants, invalid/undefined `i32` AND operands, invalid
or undefined truncation inputs, non-`u8` byte input, byte output before a byte
definition, duplicate projected SSA identities, byte-valued returns, unknown raw
runtime intrinsic names, runtime-intrinsic/profile drift, unknown pure runtime
helper identities, helper/profile drift, ambiguous helper EOF projections,
colliding projected profile I/O opcodes, invalid startup identities,
null/misaligned/undersized/
overflowing heap extents, multi-block/phi/parameterized function shapes, and
unsupported instructions or terminators fail closed before a pre-layout target
program is returned. Later
layout/profile failures must likewise fail before accepted target code is
emitted.

## Verification

- `tests/ternary_lowering.rs` loads the tracked canonical typed-IR golden
  through
  complete typed-IR admission, projects it across the explicit inbound port, and
  proves deterministic `return 7` lowering, exact 21-trit scalar recovery, exact
  function/instruction/terminator source-span preservation, and module identity
  preservation.
- Scalar tests cover zero, one, positive signed maximum, the sign-bit pattern,
  and all-one bits; projection tests reject target-profile drift and truncated
  constant bytes; a richer admitted typed-IR golden is rejected as unsupported.
- A valid byte-input/output typed-IR fixture is completely admitted,
  canonicalized, restored exactly, projected across the inbound port, and
  lowered
  deterministically to ordered byte-input/output target effects plus the
  existing
  `i32` return path. Adversarial projection tests reject non-`u8` input,
  undefined
  output values, duplicate SSA IDs, and byte-valued returns.
- Public byte-stream wrapper-plan evidence cross-checks `c-libc-v1.json` and the
  checked-in guest `stdio.c` implementation, proving intrinsic/helper order for
  both `getchar` and `putchar`, exact wrapper return semantics, and fail-closed
  rejection of wrapper/profile/EOF drift without changing libc availability.
- Wrapper profile-realization evidence revalidates the canonical plan, binds
  `getchar`/`putchar` raw I/O to current-profile input/output machine opcodes,
  preserves helper/order/return semantics, and rejects forged order or colliding
  profile opcode projections before publishing a machine operation.
- Pure runtime-helper evidence cross-checks the guest-runtime JSON contract, C
  declarations, and byte-stream implementation. It binds only the exact decode
  and low-byte helper identities, copies EOF from `current_profile()`, records
  `0..255`, `-1`, status, and mask semantics without accepting concrete guest
  values, and rejects identity/profile drift or EOF overlap with the byte
  domain.
- Raw intrinsic identity evidence reads the guest-runtime JSON contract and
  declaration header, proves the exact input/output names remain synchronized,
  lowers only those names under `malbolge-2026` to distinct `InputWord` and
  `OutputByte` semantics, and rejects unknown names or profile drift.
- Target-profile realization evidence projects exact I/O instruction bytes and
  EOF state from `current_profile()` and proves the resulting machine I/O
  operations match that descriptor without compiler-local opcode literals. It
  rejects profile identity drift and colliding projected input/output opcodes.
- Target-cell encoding adapts the canonical VM `decode_profile_instruction`
  through an inbound decoder port. Tests exhaust all 94 decode phases for both
  profile-derived I/O operations and prove every emitted cell is graphical and
  decodes back exactly; missing or ambiguous decoder behavior fails closed.
- Low-byte helper-path evidence admits a valid typed-IR `i32` AND plus
  `i32`-to-`u8` truncation sequence, canonicalizes/restores it exactly, lowers
  it
  through the same SSA boundary, and feeds the `u8` result to `ByteOutput`.
  Adversarial projections reject wrong result types and undefined AND/truncation
  operands. This closes the operation vocabulary needed by the runtime output
  helper body, not direct helper-call recognition.
- Startup-plan evidence cross-checks the guest-runtime header and JSON contract,
  then proves a valid layout-resolved ABI pointer/capacity emits exactly one
  `BindHeap` before user entry. Tests reject ABI/profile/symbol drift, null or
  misaligned arena pointers, capacities below one header-plus-payload span,
  misaligned capacities, and logical-address overflow.
- Global heap placement, executable bind-call/source sequencing, typed-IR
  external-call binding, and executable helper branching/status publication
  remain open target-lowering work.
- Expected durable artifact surface: `compiler/`, `src/`, `tests/compiler/`, and
  `tests/ternary_lowering.rs`.
- Required evidence: golden/round-trip or normalized stage fixtures,
  deterministic hashes where promised, and end-to-end lowering regression cases.
- Runtime realization evidence: consume guest-runtime semantic identities
  unchanged and prove their executable ternary/Malbolge lowering, including the
  one-time heap startup bind and declaration-only byte-I/O intrinsic symbols.
- Prerequisite completion evidence: `typed-compiler-ir`,
  `guest-runtime-and-allocator`, `malbolge-specific-optimization-mathematics`.
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
