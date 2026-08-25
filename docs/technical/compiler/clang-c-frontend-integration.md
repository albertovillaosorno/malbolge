# Clang C frontend integration

## Status

Implemented version-one normalized frontend. Portable typed IR remains a
separate downstream contract.

## Purpose

Use pinned Clang as the C parser, semantic type system, constant evaluator, and
source-location provider without making Clang's private AST object graph or dump
formats part of the Malbolge compiler contract.

## Scope

This document governs the following declared TODO scope:

- `compiler/`
- `src/`
- `tests/compiler/`

## Current Behavior

### Product boundary

The governed product function is `src/compiler/c-frontend/`. It owns one
source-to-normalized-frontend transformation. The implementation is C++ because
it consumes the exact Clang 22.1.8 C++ AST API directly, but the emitted
artifact is repository-owned JSON rather than serialized Clang objects.

The function is split into:

- `contract/frontend-v1.json`, the closed normalized artifact authority;
- `port-inbound/frontend.hpp`, a host-neutral request/result boundary;
- `adapter-inbound/clang_frontend.cpp`, the exact Clang semantic adapter; and
- `composition/`, the native command-line executable and exact CMake build.

Build automation lives in
`src/automation/repository/composition/scripts/validate/c_frontend_build.py`.
It reuses the reviewed LLVM 22.1.8 development identity and Visual Studio/DIA
resolution used by native analysis. The build uses repository-pinned
`clang-cl.exe`, C++20, `/W4 /WX`, and `/Brepro`; ambient LLVM discovery is
forbidden.

### Why the artifact is not an AST dump

Clang parsing and semantic analysis construct a source-level AST before LLVM IR
generation. LibTooling exposes frontend actions over that semantic AST. Clang's
release documentation also calls out AST-dumping potentially breaking changes.
The repository therefore consumes AST APIs but does not make `-ast-dump`, raw
JSON AST dumps, C++ class addresses, or Clang object identity durable compiler
input.

`malbolge-c-frontend-v1` is the stable boundary presented to downstream compiler
stages. A later Clang upgrade must either reproduce this contract or explicitly
version the repository artifact.

### Exact frontend identity

Version one binds:

- Clang/LLVM version `22.1.8`;
- parsing target `wasm32-unknown-unknown`;
- language mode C23;
- deterministic guest ABI `malbolge-c32-v1`; and
- target profile `malbolge-2026`.

The wasm target remains a parser/type-layout projection only. It does not become
the Malbolge backend or guest runtime.

The executable reports:

```text
malbolge-c-frontend 1 LLVM 22.1.8
```

### Input identity and provenance

The command-line composition receives a physical source path only to load bytes.
The normalized artifact receives instead an explicit portable logical source
identity. Version one rejects empty identities, absolute paths, Windows drive or
backslash syntax, empty path components, `.` components, and `..` traversal.

The artifact records:

- the logical source ID;
- SHA-256 of the exact source bytes; and
- one-based line/column plus source byte offsets for source spans.

Physical input paths, repository roots, private include roots, LLVM paths, and
native source addresses are absent from output. Tests parse identical bytes from
two different physical directories with one logical identity and require exact
artifact byte equality.

### Parsing envelope

The adapter drives one in-memory translation unit with LibTooling and a fixed
argument set:

- `--target=wasm32-unknown-unknown`;
- `-std=c23`;
- `-ffreestanding` and `-fno-builtin`;
- `-pedantic-errors`;
- reviewed hard-error conversion/function diagnostics;
- `-nostdinc`;
- the exact pinned Clang resource include directory; and
- the repository guest-libc include directory.

The in-memory filename is the logical source identity, not the physical source
path. Included declarations participate in Clang semantic analysis but are not
emitted as source nodes. References to them use semantic external identities
such as `external:memcpy` rather than header paths.

### Semantic traversal

The adapter performs deterministic semantic preorder through
`RecursiveASTVisitor`. Source-written declarations and statements receive
monotonic numeric node IDs. Parent IDs describe the normalized semantic tree.
Implicit expression nodes with source locations are retained because conversions
such as array-to-pointer decay, lvalue-to-rvalue conversion, and integral casts
matter to later typed lowering.

Version one explicitly maps its supported declaration, statement/expression,
and cast classes to repository names. An unrecognized source node is not emitted
under a raw Clang class name; normalization stops with
`MALBOLGE-FRONTEND-001`.

### Normalized types

Every expression and value declaration uses a canonical repository type grammar.
It includes:

- `void`, `bool`, `char`;
- fixed-width signed/unsigned integer types through 64 bits;
- `f32`, `f64`, and ABI-projected `f128`;
- pointers and fixed, incomplete, and variable-length arrays;
- prototype, variadic, and unspecified-parameter functions;
- named or source-anchored structs, unions, and enums;
- atomic and complex wrappers; and
- ordered `const`, `restrict`, and `volatile` qualifiers.

Typedef spellings are intentionally normalized to their canonical semantic type.
Anonymous main-source tags use their source byte offset rather than a Clang
pointer identity. Non-default address spaces and unrecognized Clang types fail
with `MALBOLGE-FRONTEND-002`. The regression suite uses `_BitInt(17)` to prove
that a construct accepted by the parser cannot silently escape the normalized
type grammar.

### Declaration semantics

Normalized declarations preserve the facts that later typed IR cannot safely
reconstruct from source spelling alone. Variables record their written storage
class, semantic storage duration, formal linkage, and whether the current
declaration is only a declaration, a tentative definition, or a full
definition. Functions record storage class, formal linkage, declaration versus
definition state, and whether `inline` was explicitly written. Parameters retain
automatic duration and written `register` where present. Tags record declaration

versus definition state.

Enum representation is deliberately ABI-owned rather than copied from Clang's
wasm code-generation choice. A fixed C23 enum records its declared canonical
integer type. For an ordinary enum, the adapter evaluates all enumerators and
chooses `i32` when every value fits signed 32-bit, otherwise `u32` when every
value is nonnegative and fits 32-bit. A mixed or wider value domain fails with
`MALBOLGE-FRONTEND-002`. The regression fixture is important because Clang's
wasm projection reports the ordinary nonnegative sample as unsigned while

`malbolge-c32-v1` requires signed `i32` for that representable value set.

Thread storage is preserved as `thread` rather than silently collapsed to
static storage. Whether a later compiler/runtime contract admits thread-local
objects is
a downstream semantic decision; the frontend does not discard that distinction.

### Constants, operations, and references

Clang constant evaluation is projected into exact decimal integer strings where
an expression is an integer constant expression. The golden fixture proves both
an enum expression evaluating to `7` and `sizeof` evaluating to the
ABI-projected value `4`.

Integer literals use exact signed/unsigned decimal interpretation. Floating
literals are encoded by exact semantic bit pattern, not host decimal formatting.
String literals use lowercase hexadecimal source bytes so arbitrary byte strings
do not depend on JSON text encoding.

Binary and unary operations use source-language operator spellings. Casts use a
closed repository vocabulary. Main-source declaration references are
`name@byte-offset`; header/builtin references are `external:name`.

## Invariants

- Exact Clang 22.1.8 semantic APIs are implementation input, not artifact
  identity.
- Raw AST dump output and native Clang object identity never cross the function
  boundary.
- Artifact source identity is portable and physical-path independent.
- Source SHA-256 and normalized spans bind every artifact to exact input bytes.
- Header declarations may affect semantic analysis but do not expose physical
  include paths.
- Unknown semantic classes fail closed rather than inheriting Clang spelling by
  accident.
- Ordinary enum representation follows the repository ABI rule from enumerator
  values; Clang's inferred wasm code-generation type is not normative.
- Declaration storage, linkage, definition state, and thread duration remain
  explicit for downstream policy rather than being discarded.
- The stage stops before the portable typed compiler IR owned downstream.

## Failure Behavior

Version one has four stable failure families:

- `MALBOLGE-FRONTEND-001`: unsupported normalized declaration, statement, or
  cast class;
- `MALBOLGE-FRONTEND-002`: unsupported normalized type;
- `MALBOLGE-FRONTEND-003`: invalid frontend request or command-line input; and
- `MALBOLGE-FRONTEND-004`: Clang could not parse/semantically admit the selected
  translation unit.

Invalid logical identities fail before Clang. Unsupported semantic nodes/types
fail before artifact publication. Syntax diagnostics use the logical source
identity. A failed request emits no partial normalized artifact.

This stage does not claim portable typed IR, control-flow normalization,
lowerability, or Malbolge code generation. Those remain downstream compiler
contracts.

## Verification

`tests/test_c_frontend.py` builds the exact native frontend and proves:

- closed version-one contract identity;
- exact executable/LLVM version identity;
- byte-for-byte equality with a checked-in golden artifact;
- deterministic source SHA-256, type normalization, and constant evaluation;
- ABI-owned ordinary/fixed enum representation rather than Clang's inferred
  default code-generation type;
- declaration/definition, tentative-definition, storage-duration, linkage,
  inline, and parameter storage semantics;
- byte-identical output after relocating the physical source file;
- external header references without repository/LLVM path leakage;
- stable rejection of `_BitInt(17)` outside the normalized grammar;
- rejection of a default enum domain that fits neither ABI `i32` nor `u32`;
- malformed C rejected under its logical source identity; and
- escaping source identities rejected before Clang.

`tests/test_repository_scaffold.py` additionally admits `compiler` as a governed
source responsibility domain. Repository-wide Jig validation remains the final
architecture/policy gate.

## References

- [Clang LibTooling](
  ../../bibliography/platforms-and-runtimes/compiler/clang-libtooling.md)
- [Clang](../../bibliography/tooling/clang.md)
- [Deterministic C Surface And Clang
  Tooling](../adr/deterministic-c-surface-and-clang-tooling.md)
- [Compiler Pipeline And Guest
  Runtime](../adr/compiler-pipeline-and-guest-runtime.md)
- [Verification Trust Boundary](../adr/verification-trust-boundary.md)

### Governing ADR Paths

- `docs/technical/adr/deterministic-c-surface-and-clang-tooling.md`
- `docs/technical/adr/compiler-pipeline-and-guest-runtime.md`
