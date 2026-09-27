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
application lowerer currently admits only no-argument functions containing one
entry block, no phi nodes, one exact `i32` constant materialization, and a
return
of that value. Other admitted typed-IR shapes fail explicitly.

Exact 32-bit constant bit patterns are converted to a fixed 21-trit,
least-significant-trit-first scalar. Twenty trits are insufficient for every
`u32` bit pattern, while 21 trits cover the complete 32-bit representation
domain. The pre-layout program retains upstream function/value IDs plus exact
source spans, source digest, ABI identity, typed-IR version, and target-profile
identity.

This is executable compiler lowering but not target code generation. Layout,
address assignment, runtime intrinsic realization, target serialization, and
Malbolge encoding remain downstream work.

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
non-`i32` or malformed constants, multi-block/phi/parameterized function shapes,
and unsupported instructions or terminators fail closed before a pre-layout
target program is returned. Later layout/profile failures must likewise fail
before accepted target code is emitted.

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
