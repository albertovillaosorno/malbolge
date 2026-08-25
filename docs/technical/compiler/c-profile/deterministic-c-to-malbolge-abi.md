# Deterministic C-to-Malbolge ABI

## Status

Accepted ABI contract. The canonical machine-readable authority and ABI-only
source preflight are implemented. Full C-to-Malbolge lowering remains a
separate compiler-pipeline concern.

## Purpose

Define one closed, host-independent C ABI for the current Malbolge target. The
ABI fixes scalar representation, byte order, pointers, aggregate layout,
calling convention, stack behavior, object lifetime, byte I/O, and failure
semantics so that no native C ABI becomes guest authority by accident.

The ABI identifier is `malbolge-c32-v1`. Its canonical machine-readable
manifest is:

`docs/technical/specification/c-abi-v1.json`

Changing any normative value in that manifest requires a new ABI identifier or
an explicitly versioned schema change. Consumers fail closed on unknown keys,
duplicate JSON keys, unknown schema versions, or disagreement with the current
target profile.

## Scope

This contract governs the ABI surface consumed by:

- `tools/tidy/` and its transitional ABI preflight;
- the deterministic C compiler frontend and lowering pipeline;
- `src/runtime/guest-c-library/` declarations and guest runtime code;
- runtime stack, memory, and I/O adapters;
- `tests/tidy/` compatibility fixtures; and
- `docs/technical/specification/` machine-readable authorities.

It does **not** claim that pinned Clang, LLVM IR, WebAssembly, the host process,
or the host operating system is the guest ABI.

## Current Behavior

### Authority and frontend projection

The repository-owned manifest is normative. Pinned Clang 22.1.8 is used only
as a parser and data-layout projection with target
`wasm32-unknown-unknown`. The projection is continuously checked against:

```text
e-m:e-p:32:32-p10:8:8-p20:8:8-i64:64-i128:128-n32:64-S128-ni:1:10:20
```

Only default address space 0 is admitted. Clang address-space extensions are
rejected because the projection contains non-default address spaces whose
pointer widths differ from the ABI's 32-bit object pointer.

Emitted WebAssembly or LLVM code is not a guest artifact and is not evidence
that C-to-Malbolge lowering exists. The projection exists to make frontend
parsing and layout checks deterministic while the Malbolge compiler owns the
actual guest representation.
The validator also checks tool identity before parsing: Clang and clang-tidy
must report repository-pinned LLVM version 22.1.8. An alternate executable path
that reports a different version fails closed before guest source analysis.

### Target-profile binding

`malbolge-c32-v1` is bound to current target profile `malbolge-2026` in the
root `malbolge.json` authority. Validation fails when the ABI manifest and the
canonical current-profile selection disagree.

The current profile has 14-trit Malbolge words, modulus and memory extent
4,782,969 words, `/` as the input instruction, `<` as the output instruction,
EOF word 4,782,968, and byte output modulo 256. These Malbolge machine facts do
not change the C scalar widths below. C objects live in the compiler/runtime's
logical byte-addressed model and are lowered into selected-profile resources.

### Byte and scalar representation

One C byte is exactly 8 bits and multi-byte scalar objects are little-endian.
Signed integers use two's-complement object representation.

| C type | Size | Alignment | Notes |
| --- | ---: | ---: | --- |
| `_Bool` | 1 | 1 | canonical values 0 and 1 |
| `char` / `signed char` / `unsigned char` | 1 | 1 | plain `char` is signed |
| `short` | 2 | 2 | 16-bit |
| `int` | 4 | 4 | 32-bit |
| `long` | 4 | 4 | 32-bit |
| `long long` | 8 | 8 | 64-bit |
| `wchar_t` | 4 | 4 | signed 32-bit |
| `float` | 4 | 4 | IEEE-style binary32 |
| `double` | 8 | 8 | IEEE-style binary64 |
| `long double` | 16 | 16 | IEEE-style binary128 |
| object pointer | 4 | 4 | logical 32-bit encoding |
| function pointer | 4 | 4 | logical 32-bit table encoding |

Unsigned arithmetic is modulo `2^N` for the type width. Right shift of a
negative signed integer is arithmetic. These choices make implementation-
defined C behavior part of this target rather than part of the host ABI.
Signed arithmetic overflow remains undefined C behavior; the fixed two's-
complement representation does not turn undefined signed overflow into wrapping
arithmetic.

For an enum without an explicitly fixed C23 underlying type, the frontend uses
signed 32-bit `int` when all enumerator values are representable there and
unsigned 32-bit `int` otherwise when the value domain is representable there.
A fixed underlying enum may use only a canonical integer type described by this
ABI. A value domain that cannot be represented by those rules must be rejected
rather than inheriting a host enum ABI.

Compiler-specific 128-bit integers and C23 `_BitInt` objects are outside ABI v1.

### Floating-point determinism

The floating representations use radix 2 and the following precision/exponent
geometry:

| Type | Mantissa bits | Maximum exponent |
| --- | ---: | ---: |
| `float` | 24 | 128 |
| `double` | 53 | 1024 |
| `long double` | 113 | 16384 |

Operations use round-to-nearest, ties-to-even. Subnormals are preserved and
there is no excess intermediate precision beyond the semantic type. When an
operation must produce a NaN, the compiler/runtime canonicalizes the result to
a quiet NaN with zero payload. The implementation must not expose host floating
register width, host flush-to-zero state, or host NaN payload choices.

The C floating environment is not permission to delegate rounding policy to a
host FPU. Any future supported floating-environment surface must be specified as
an explicit deterministic guest contract.

### Pointer model

Object pointers and function pointers are distinct logical namespaces. Both are
32-bit little-endian values with raw zero reserved for null.

For an object at logical byte offset `a`, a non-null object pointer encodes
`a + 1`. Consequently valid encoded non-null values are `1..0xffffffff` and
valid zero-based logical byte offsets are `0..0xfffffffe`. Pointer arithmetic
is defined only inside the originating live object (plus the usual one-past
position permitted by C); the representation is not permission to forge a live
object pointer from an arbitrary integer.

A function pointer encodes a stable function-table index plus one. Function
identity is assigned deterministically by the compiler/linker and is not a
native code address. Indirect calls dispatch through that table.

`size_t` and `uintptr_t` are `unsigned long`; `ptrdiff_t` and `intptr_t` are
`long`, so all four are 32-bit in ABI v1. Object-pointer/integer conversions
must preserve the specified logical encoding and provenance checks. Native
addresses and native function handles never cross the guest ABI.

Non-default Clang address spaces are rejected. They cannot be used to access
projection-specific 8-bit pointer layouts.

### Alignment and aggregate layout

The maximum supported alignment is 16 bytes. Standard `_Alignas`/`alignas`
requests at or below that value are admitted. A request above 16 bytes is an
ABI rejection.

For a positive power-of-two alignment `A`, define:

```text
align_up(x, A) = (x + A - 1) & ~(A - 1)
```

Struct fields appear in declaration order. Each field starts at
`align_up(previous_end, field_alignment)`. Struct alignment is the maximum
field alignment, capped by the ABI maximum, and struct size is rounded up to
that alignment. Arrays use element size rounded to the element alignment as
their stride. A union places every member at offset zero; its size and alignment

are the maximum required by its admitted members, rounded as above.

Flexible array members are admitted where standard C permits them. Their
storage follows the fixed struct prefix at the canonical element alignment and
is sized by the containing allocation rather than by `sizeof` the prefix.

All ABI-created padding bytes are zero-filled. Copying or materializing an
aggregate therefore cannot reveal host stack garbage or host-specific padding
bits. Reading an uninitialized C value is still undefined behavior and must not
be legitimized merely because padding has a deterministic fill value.

Bit-fields, packed record layout, `#pragma pack`, compiler vector types, and
bit-precise integer objects are outside v1. Those constructs choose or require
layout rules that this version intentionally does not specify.

### Calling convention

The guest call stack grows toward lower logical byte addresses and remains
16-byte aligned. Every call frame begins with this fixed 32-byte hidden header:

| Offset | Field | Encoding |
| ---: | --- | --- |
| 0 | `previous_frame` | object pointer or zero |
| 4 | `continuation_id` | `u32` |
| 8 | `function_id` | `u32` |
| 12 | `frame_extent` | `u32` byte count |
| 16 | `argument_block` | object pointer |
| 20 | `result_block` | object pointer or zero for `void` |
| 24 | `variadic_begin` | object pointer or zero |
| 28 | `flags` | `u32`, must be zero in v1 |

`previous_frame` links the active guest frames. `continuation_id` identifies the
compiler-owned return continuation; it is not a native return address.
`function_id` identifies the deterministic function-table entry.
`frame_extent` covers the complete aligned frame so unwind and stack-exhaustion
checks do not depend on host stack metadata.

Fixed arguments are laid out in source parameter order in `argument_block`.
Each argument begins at the natural ABI alignment of its parameter type, and
its stored representation is the canonical object representation above.

Variadic arguments use the C default argument promotions, then the same natural
alignment rule in source order. `variadic_begin` points to the first promoted
variadic object. `va_list` is a guest cursor over this canonical block; it is
never the host compiler's native `va_list` representation.

All non-void results use caller-owned result storage. `result_block` points to
storage aligned for the declared return type. This rule also covers aggregate
returns and avoids target-specific native register-return conventions.

Recursion, function pointers, aggregates, VLAs, and variadic functions are not
blanket-rejected. They are ABI-supported constructs. A later lowerability pass
may reject a particular program only for a documented semantic, resource, or
unsupported-runtime reason.

### Object lifetime and allocation

Static-duration objects are allocated deterministically by the linker in a
stable order. Automatic objects live inside the active guest frame or a
compiler-owned frame allocation region and cease to be live when that frame is
left. Variable-length automatic objects extend the frame by an overflow-checked
aligned extent.

Dynamically allocated objects, when provided by the supported libc/runtime
contract, use the same logical byte-addressed object-pointer representation.
Allocation is not forbidden by this ABI merely because the eventual Malbolge
implementation is difficult. Exhaustion is a deterministic runtime result of
the selected allocator contract.

Dereferencing a null, expired, forged, misaligned, or out-of-bounds pointer is
not delegated to native behavior. Statically identifiable violations are
rejected; dynamic checks required by the selected compiler mode fail closed at
runtime. Stack extent arithmetic is checked before publication of a new frame.
Stack exhaustion is a deterministic runtime failure, not native stack overflow.

### C byte I/O

C byte I/O is mapped to the selected `malbolge-2026` machine semantics:

- input executes the profile's `/` input operation;
- guest input words representing byte values `0..255` become C `int` values
  `0..255`;
- the profile EOF word `4,782,968` becomes C `int` value `-1`;
- output consumes the low eight bits of the C value and executes the profile's
  `<` output operation; and
- the externally observed output byte is modulo 256 as required by the target
  profile.

The C ABI therefore never exposes the Malbolge EOF sentinel as a positive C
character and never inherits host `EOF`, text-mode newline translation, locale,
or terminal encoding behavior.

## Invariants

- The repository-owned `malbolge-c32-v1` manifest is the ABI authority;
  host/native layouts are never normative.
- Guest C uses fixed 8-bit bytes, little-endian canonical objects, 32-bit
  logical pointers, and a 16-byte maximum alignment.
- Calls use the fixed guest frame and caller-owned result storage; native return
  addresses, registers, and `va_list` layouts never cross the boundary.
- Recursion, aggregate types, allocation, VLAs, variadics, and function
  pointers are not rejected merely because Malbolge lowering is difficult.
- ABI exclusions are explicit, source-located, versioned diagnostics. Semantic
  lowerability remains a distinct downstream proof obligation.
- Target/profile, pointer, arithmetic, floating, lifetime, and byte-I/O choices
  fail closed instead of falling back to host behavior.

## Failure Behavior

### Undefined, implementation-defined, and unsupported behavior

This ABI fixes the implementation-defined choices it owns. It does not redefine
ISO C undefined behavior into arbitrary deterministic behavior.

The compiler validation pipeline applies these rules:

1. ABI constructs outside `malbolge-c32-v1` receive source-located
   `MALBOLGE-ABI-*` diagnostics before lowering.
2. The full `tools/tidy` lowerability analyzer is responsible for semantic
   undefined-behavior and unsupported-runtime checks that require program
   analysis rather than ABI layout inspection.
3. If a dynamic violation cannot be decided statically and the selected mode
   admits runtime checking, the runtime fails closed deterministically.
4. No failure path may fall through to native pointer, native stack, native
   floating-point environment, or native calling-convention behavior.

The current ABI-only preflight provides these durable diagnostics:

| Code | Rejection |
| --- | --- |
| `MALBOLGE-ABI-001` | bit-field layout |
| `MALBOLGE-ABI-002` | packed record attribute |
| `MALBOLGE-ABI-003` | `#pragma pack` layout |
| `MALBOLGE-ABI-004` | alignment above 16 bytes |
| `MALBOLGE-ABI-005` | `_BitInt` representation |
| `MALBOLGE-ABI-006` | `__int128` extension |
| `MALBOLGE-ABI-007` | compiler vector type |
| `MALBOLGE-ABI-008` | non-default address space |

This preflight is intentionally narrower than the clang-tidy plugin and libc
preflight. It owns ABI exclusions only and must not be cited as proof that
arbitrary C has a complete Malbolge lowering.

## Verification

### Compatibility fixtures

`tests/tidy/accepted/` contains ABI-positive evidence. The fixtures currently
lock scalar/pointer widths, offsets, byte order, signed behavior, recursion,
function pointers, variadics, VLAs, flexible arrays, and standard 16-byte
alignment.

`tests/tidy/rejected/` contains one or more fixtures for every ABI diagnostic
family above. Regression tests require source path, line, and column data and
require the documented manual validator to reject the ABI fixture before the
normal clang-tidy pass.

### Manual validation

Validate the canonical authority directly:

```text
python src/automation/repository/composition/scripts/validate/c_abi.py
```

Validate explicit guest C files through ABI/libc preflights and the current
manual tidy path:

```text
python src/automation/repository/composition/scripts/validate/main.py file.c
```

The manual validator supplies the canonical Clang target itself. Callers do not
select a native triple as part of guest-C validation.

### Regression suite

The ABI regression suite checks:

- closed-schema validation, duplicate-key rejection, and profile binding;
- exact pinned-Clang target triple and data-layout projection;
- accepted fixture parsing under the canonical projection;
- source-located diagnostic codes for every rejected ABI fixture;
- invalid source UTF-8 failing closed before Clang interpretation;
- manual-validator ordering; and
- strict Ruff and basedpyright conformance for the validation implementation.

Compiler/runtime implementation of every admitted C semantic remains covered by
downstream compiler, lowerability, libc, and runtime TODOs. Those tasks may
refine implementation strategy but may not silently change this ABI.

## References

- [Deterministic C Surface And Clang
  Tooling](../../adr/deterministic-c-surface-and-clang-tooling.md)
- [Compiler Pipeline And Guest
  Runtime](../../adr/compiler-pipeline-and-guest-runtime.md)
- [Canonical Malbolge Target Profile](../../specification/target-profile.md)
- [`malbolge-c32-v1` machine-readable
  authority](../../specification/c-abi-v1.json)

### Governing ADR Paths

- `docs/technical/adr/deterministic-c-surface-and-clang-tooling.md`
- `docs/technical/adr/compiler-pipeline-and-guest-runtime.md`
