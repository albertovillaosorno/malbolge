# Typed compiler IR

## Status

Implemented version one. The closed model, admission boundary, canonical
identity, finite guest layout, normalized frontend handoff, and regression
evidence satisfy the typed-IR objective. The initial frontend lowerer fails
closed on semantic shapes it does not yet support; eliminating those failures
for every accepted C program is explicitly owned by the later tools/tidy
lowerability contract. Target lowering remains a separate downstream stage.

## Purpose

Define a small deterministic IR representing control flow, arithmetic, memory,
calls, byte I/O, target-profile requirements, and proof obligations without
inheriting unnecessary LLVM complexity or host/native representation choices.

## Scope

This document governs the following declared TODO scope:

- `compiler/`
- `src/`
- `tests/compiler/`

## Current Behavior

### Governed product boundary

The governed function is `src/compiler/typed-ir/`. Its machine authority is
`src/compiler/typed-ir/contract/typed-ir-v1.json`, with artifact identity
`malbolge-typed-ir-v1`. The module is explicitly bound to normalized frontend
identity `malbolge-c-frontend-v1`, guest ABI `malbolge-c32-v1`, and target
profile `malbolge-2026`.

The implementation is safe Rust arranged as small responsibility-owned domain
and application modules. Public aggregate values keep their product state
private and accept explicit construction payloads; construction is intentionally
separate from admission so regression tests can represent malformed untrusted
IR without mutating private state by index.

### Structural form and identity

Version one uses typed SSA values in explicit basic blocks. Type, global,
function, block, and SSA-value namespaces use portable `u32` IDs. Admission
requires dense IDs in deterministic order and rejects duplicate SSA definitions.
No object address, allocation order, Rust enum discriminant, or hash-map
iteration becomes semantic identity.

Each basic block owns exactly one final terminator. Phi nodes use explicit
predecessor/value pairs. The declared entry block cannot contain phi nodes
because its first invocation has no predecessor edge from which a phi could
select a value. The validator builds the predecessor graph and proves every
block reachable from the declared entry, computes dominators, checks every phi
against the exact predecessor set, and validates SSA dominance at instruction,
terminator, and phi-edge use points. Loop backedges therefore use predecessor-
edge semantics rather than ordinary block-entry use semantics.

The closed type vocabulary covers scalar integers through 64 bits, binary32,
binary64, ABI-projected binary128, guest object pointers, fixed arrays, structs,
unions, functions, and `void`. Type-table references are explicit and checked;
function parameters/results, aggregate members, pointers, and arrays cannot fall
back to host/native type identity.

### Instructions and control flow

The version-one instruction vocabulary covers exact integer constants, typed
binary operations, comparisons, casts, automatic allocation, loads/stores,
byte-address offsets, direct/indirect calls, function addresses, and
deterministic byte input/output. These byte instructions are raw `u8` runtime
effects, not the public C `getchar` representation; guest-runtime owns mapping
between profile EOF and C `-1`. Floating division is explicit rather than
overloaded with signed/unsigned integer division.

Pointer/integer conversions have dedicated operations. `bitcast` is restricted
to one logical pointer namespace: object-to-object or function-to-function.
Object and function pointer representations cannot be exchanged merely because
both are 32 bits. `void *` remains inside the object-pointer namespace as C's
generic object pointer, so it may bitcast to or from concrete object pointers
without becoming dereferenceable as `void`. Integer conversion is likewise
object-pointer-only and exactly
32 bits so the ABI encoding is neither implicitly truncated nor widened; any
further integer-width change requires a separate explicit cast. Function-pointer
identity is introduced by `FunctionAddress` and preserved through typed
function-pointer values. Truth-value conversion remains valid for either pointer
namespace and is explicit through `PointerToBool`.
Equal-width non-boolean integer representation conversion has its own operation.
Automatic allocation has active-function-frame lifetime, consumes an explicit
ABI `u32` byte count, and returns an object pointer with a positive power-of-two
alignment no greater than 16 bytes. Loads and stores require an exact object
pointee type. Boolean arithmetic is rejected; normalized C integer promotions
must be represented explicitly before integer arithmetic, bitwise/shift work,
and comparisons. Plain `char` follows the ABI's signed 8-bit choice and must be
promoted before those operations; its source category remains signed rather
than unsigned.

Branches require `bool`; returns must match the declared function signature;
switch selectors are already-promoted integers with exact typed constants and
no duplicate case identity. Function signatures contain C-adjusted non-array
value types, and variadic trailing arguments must already carry the default
argument promotions. Calls validate fixed parameters, variadic shape, and result
type.
Direct calls name dense module-local functions; indirect calls consume a
dominance-valid SSA pointer whose pointee is the exact invoked signature.
`FunctionAddress` is the explicit bridge from a module-local function ID to that
pointer value.

### Canonical object layout

Admission computes finite `malbolge-c32-v1` object size/alignment independently
of host layout. Scalar and pointer sizes follow the ABI table; arrays use
aligned
element stride; structures place fields in declaration order at natural
alignment and round the final extent to maximum field alignment; unions use the
maximum member extent/alignment. All arithmetic is overflow-checked in the
32-bit logical byte domain.

By-value aggregate cycles fail closed while pointer recursion remains valid.
When a static global carries explicit initializer bytes, their length must equal
its exact canonical object extent. This prevents malformed IR from publishing
an initializer whose byte sequence cannot denote the declared guest object.

### Source provenance and proof obligations

Every module carries one portable logical source ID and the exact source
SHA-256. Globals, functions, blocks, phis, instructions, and terminators carry
normalized byte/line/column spans. Physical source paths never enter the IR.

The model retains verifier-visible obligations for alignment, in-bounds pointer
ranges, nonzero values, no-signed-overflow, and target-profile capabilities.
Alignment and in-bounds obligations require object pointers; function pointers
cannot be treated as memory ranges. A no-signed-overflow obligation must name
the result of an overflow-relevant signed binary instruction rather than an
arbitrary
signed value. Admission verifies record shape and references but does not
discharge the obligation. Later stages must preserve, prove, or materialize each
obligation according to their own documented contract.

### Normalized frontend lowering

The typed-IR function now owns a Rust domain semantic projection for
`malbolge-c-frontend-v1`. The projection carries exact frontend producer
identity (Clang 22.1.8, wasm32 target, C23 mode), ABI/profile identity, portable
source ID/SHA-256, normalized source spans, and declaration semantics. It does
not parse JSON or expose Clang object identity.

The first lowering slice is deliberately closed: it accepts only a defined,
external, non-inline, storage-class `none`, no-argument `fn()->i32` whose body
returns one normalized `i32` integer constant. The lowerer preserves function,
body, return, and value spans; converts the semantic decimal constant to exact
32-bit little-endian bits; constructs canonical typed IR; and invokes complete
IR admission before returning a module. Wrong producer identity,
unsupported
semantic shapes, and out-of-range constants fail with stable lowering errors.

A tracked C fixture is normalized by the real pinned frontend into an exact JSON
golden. Rust lowering evidence uses that golden's exact source identity, digest,
spans, declaration facts, and constant semantics and locks the resulting typed
IR with its own canonical golden. The serialized JSON-to-port adapter and
broader
C lowering remain open rather than being hidden in a bespoke JSON parser or
a new third-party Rust dependency.

### Canonical identity

Canonicalization is validation-gated: malformed IR cannot be serialized as an
accepted artifact. The binary identity begins with `MCTI`, then a little-endian
`u16` format version. Multibyte fields use explicit little-endian encodings,
variable-length data uses checked `u32` lengths, and every closed enum uses
repository-owned versioned `u8` tags.

Deterministic debug identity is the prefix `malbolge-typed-ir-v1:` followed by
lowercase hexadecimal canonical bytes. It does not use Rust `Debug`, struct
layout, host pointer width, or native endianness.

### Relationship to LLVM IR

LLVM's language reference is useful design evidence for explicit basic-block
terminators and predecessor-labelled SSA merge values. LLVM IR itself is not the
portable compiler contract. Version one deliberately does not inherit LLVM
poison/undef rules, target data-layout strings, metadata graphs, attributes,
intrinsics, or native calling conventions merely because LLVM exposes them.

## Invariants

- The repository-owned machine contract, not Rust layout, defines IR identity.
- Clang AST objects and raw AST dumps stop at the completed C frontend boundary.
- Every SSA value has one definition and every use is dominance-valid.
- Every block is reachable and every phi exactly matches CFG predecessors.
- Source/profile identity and operation-level provenance remain explicit.
- Canonical bytes are published only after complete fail-closed admission.
- Proof obligations are retained as semantic obligations, never optimization
  hints that may be silently dropped.
- Target/Malbolge encoding remains a downstream concern.

## Failure Behavior

Admission fails closed on unsupported version/ABI/profile identity, invalid
logical source identity, incoherent or out-of-owner spans, sparse IDs,
invalid type references,
duplicate/undefined SSA values, dominance violations, unreachable blocks,
phi/predecessor mismatch, operand/result type errors, call-signature errors,
invalid memory alignment/pointee relationships, ambiguous truth-value casts,
boolean arithmetic, malformed finite object layout, wrong-size global
initializers, bad control-flow types, malformed integer constants, and invalid
proof references.

Canonical serialization invokes complete admission first and returns a
validation failure rather than partial bytes. Checked length conversion rejects
any variable-length field that cannot fit the version-one `u32` wire length.

## Verification

`tests/compiler_ir.rs` currently proves 68 integration cases, including:

- accepted diamond control flow with an exact phi merge;
- stable canonical binary identity and a tracked debug-text golden;
- duplicate SSA and use-before-definition rejection;
- entry-block phi rejection, including a self-backedge entry;
- phi predecessor and phi-edge dominance rejection;
- unreachable-block rejection;
- call-signature mismatch;
- invalid proof references;
- invalid portable source identity blocking canonicalization;
- broken type references;
- non-boolean branch rejection;
- malformed boolean constant rejection; and
- invalid load alignment rejection;
- accepted indirect call through an explicitly typed function address;
- non-function indirect-call target rejection;
- accepted automatic allocation with an ABI `u32` byte count;
- non-`u32` automatic-allocation size rejection; and
- raw function-typed SSA plus void-global rejection;
- exact normalized frontend constant-return lowering and provenance;
- wrong frontend producer identity rejection;
- unsupported frontend signature rejection; and
- out-of-range normalized `i32` constant rejection;
- explicit pointer-to-bool admission and pointer-to-integer mismatch rejection;
- boolean arithmetic rejection before lowering;
- function-pointer memory-proof rejection;
- exact initialized-global object extent;
- by-value recursive aggregate rejection; and
- aggregate layout overflow rejection; and
- instruction/phi/terminator provenance containment within owning blocks and
  functions;
- plain `char` admitted as signed 8-bit for sign extension; and
- plain `char` rejected from unsigned zero-extension semantics;
- `void *` bitcasts within the object-pointer namespace;
- object-to-function pointer bitcast rejection;
- function-pointer-to-integer conversion rejection; and
- integer-to-function-pointer forgery rejection.

The implementation passes the repository's workspace-wide nightly Clippy gate
with warnings denied. Broader normalized C coverage, including linkable external
symbols, aggregates, VLAs, and addressable-object cases are not silently
dropped:
it is transferred to `tools-tidy-lowerability-contract`, whose completion
requires every linter-clean accepted translation unit to lower through the
frontend and typed IR. Ternary/target lowering remains downstream.

## References

- [Clang C Frontend Integration](clang-c-frontend-integration.md)
- [LLVM Intermediate Representation](
  ../../bibliography/platforms-and-runtimes/compiler/llvm-ir.md)
- [Deterministic C Surface And Clang
  Tooling](../adr/deterministic-c-surface-and-clang-tooling.md)
- [Compiler Pipeline And Guest
  Runtime](../adr/compiler-pipeline-and-guest-runtime.md)
- [Verification Trust Boundary](../adr/verification-trust-boundary.md)
