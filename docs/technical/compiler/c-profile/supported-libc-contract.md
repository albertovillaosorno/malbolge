# Supported libc contract

## Status

Implemented for `malbolge-libc-v1`. Memory, narrow-string, exact binary64
`fabs`/`floor`/`ceil`/`trunc`, and canonical nearest-ties-even `sqrt` are
executable guest C today. Allocation, byte streams, formatting, and the
remaining transcendental math stay versioned but unavailable until their
runtime/integration gates complete.

## Purpose

Define one closed guest C library surface with exact declarations,
deterministic guest semantics, and no hidden host-libc or host-`libm` fallback.
The contract distinguishes executable functionality, contracted future
functionality, and operations that are forbidden because their meaning depends
on ambient host state.

## Scope

This contract governs:

- `docs/technical/specification/c-libc-v1.json` as the machine authority;
- `src/runtime/guest-c-library/` as guest headers and executable guest code;
- `src/automation/repository/composition/scripts/validate/c_libc.py` as the
  closed-schema authority validator;
- `c_libc_source.py` as source-located routine availability preflight;
- the manual guest-C validator's library include and preflight ordering;
- `tests/tidy/libc/` and `tests/tidy/libc-rejected/` as executable boundary
  fixtures.

This contract lane does not own heap/stream integration, formatting, or the
remaining correctly-rounded transcendental `libm` algorithms. Those facilities
remain owned by `guest-runtime-and-allocator`.

## Current Behavior

### Canonical identity

`c-libc-v1.json` defines library identity `malbolge-libc-v1`, binds it to ABI
`malbolge-c32-v1` and target profile `malbolge-2026`, and closes the header and
routine sets. Duplicate keys, unknown fields, identity drift, and changed
availability sets fail closed.

The contract deliberately does not equate its surface with whatever one host
calls "C23 freestanding". WG14 C23 issue 1040 remains open and identifies
ambiguities in the freestanding library wording, including the omission of
`<stdckdint.h>` from one required-header list. The repository therefore owns a
versioned surface rather than silently changing when standards wording or a host
libc changes.

### Compiler-provided headers

The pinned Clang frontend provides target-independent compiler headers used by
the guest profile:

- `<float.h>`;
- `<iso646.h>`;
- `<limits.h>`;
- `<stdalign.h>`;
- `<stdarg.h>`;
- `<stdbool.h>`;
- `<stdckdint.h>`;
- `<stddef.h>`;
- `<stdint.h>`;
- `<stdnoreturn.h>`.

These headers are compiler interface material, not evidence of a host libc ABI.
The guest include directory precedes ambient host include paths. `<stdbit.h>` is
not admitted by version one because the pinned freestanding frontend package
does not provide the required library header for this target projection.

### Repository-owned guest headers

The guest library owns four version-one headers:

- `<string.h>` declares the executable memory and narrow-string subset;
- `<stdlib.h>` declares only the contracted allocation subset;
- `<stdio.h>` declares only byte I/O and bounded formatting;
- `<math.h>` declares the executable exact/`sqrt` subset and contracted
  transcendental binary64 subset.

Guest headers intentionally retain stable declarations for both executable and
unavailable routines. A source may include them in any build configuration, but
a call to an unavailable routine is rejected before lowering. Hosted objects
such as `FILE`, locale state, process handles, and host descriptors are not
exposed.

### Executable routines

Fourteen routines are executable ordinary guest C today:

- `memcpy`, `memmove`, `memset`, and `memcmp`;
- `strlen`, `strcmp`, `strcpy`, `strncpy`, and `strcat`; and
- `fabs`, `floor`, `ceil`, and `trunc` for exact binary64 operations; and
- `sqrt` with ABI-fixed nearest-ties-even rounding and canonical NaN.

Memory/string declarations live in `contract/include/string.h`; implementations
live in `domain/memory.c` and `domain/string.c`. Math declarations live in
`contract/include/math.h`; exact operations use `domain/math_exact.c` and the
proved square-root algorithm uses `domain/math_sqrt.c`. The
memory/string implementations are freestanding byte loops. `memmove` uses
the version-one guest `uintptr_t` pointer encoding to choose copy direction;
`memcmp` and `strcmp` compare unsigned byte values and return a deterministic
negative, zero, or positive result.

Clang documents that `-ffreestanding` still requires a C library supplying
interfaces including `memcpy`, `memmove`, and `memset`. Providing those symbols
inside the guest runtime is therefore part of the compiler contract, not a host
shortcut. Clang also exposes guaranteed-inline memory builtins that may be used
as implementation building blocks when their constraints are met, but version
one currently uses ordinary guest C so correctness does not depend on those
builtins.

### Contracted but unavailable routines

The following signatures and guest-visible semantics are reserved now but calls
emit `MALBOLGE-LIBC-001` until lane 8 supplies executable guest implementations:

- allocation: `malloc`, `calloc`, `realloc`, and `free`;
- byte streams: `getchar` and `putchar`;
- bounded formatting: `snprintf` and `vsnprintf`;
- transcendental binary64 math: `sin`, `cos`, and `atan2`.

Allocation is specified as guest-heap behavior rather than a host allocation
service. Byte streams use the deterministic byte-I/O semantics already owned by
the guest ABI. Formatting is locale-free. Binary64 routines must obey the
version-one floating representation, rounding, subnormal, and canonical-NaN
rules rather than whichever floating environment a native host happens to use.

### Forbidden host-dependent routines

The following names represent library operations whose ordinary meaning depends
on ambient host facilities and are rejected with `MALBOLGE-LIBC-002` when used
as unresolved external library calls:

- `system` for host process control;
- `getenv` for ambient host environment state;
- `setlocale` for host locale state;
- `fopen` and `tmpfile` for host filesystem/file-handle semantics;
- `time` for the ambient host clock;
- `signal` for the host signal model.

The source preflight uses Clang declaration identity rather than name-only text
matching. A source-defined function that happens to use one of those spellings
is not classified as a libc call.

### Source validation order

For each explicitly selected guest translation unit, the manual validator now:

1. validates the canonical C ABI authority;
2. validates `malbolge-libc-v1`;
3. runs ABI source preflight;
4. runs libc routine-availability preflight;
5. runs the additive clang-tidy profile/plugin only after both preflights pass.

The pinned guest include directory is supplied to both Clang AST preflights and
the clang-tidy frontend. Arbitrary repository C is still never enrolled by file
extension or source comment.

## Invariants

- `malbolge-libc-v1` is bound to `malbolge-c32-v1` and `malbolge-2026`.
- Guest headers never resolve a routine through host libc or host `libm`.
- Executable version-one routines are repository-owned guest C with no external
  symbol dependency.
- Contracted-unavailable routines have stable declarations and deterministic
  future semantics but are rejected before lowering today.
- Forbidden routines are rejected because of host-dependent semantics, not
  because the compiler has merely not implemented them yet.
- User-defined functions are not rejected solely because their identifier
  matches a forbidden library spelling.
- Native debug adapters are not guest-runtime conformance evidence.
- A compiler optimization or intrinsic may replace a library body only when it
  preserves the same guest-visible semantics for the selected target profile.
- `<stdbit.h>` remains unavailable until a repository-owned or pinned compatible
  implementation is deliberately admitted.

## Failure Behavior

Malformed or drifted `c-libc-v1.json` fails as a configuration error before
source validation. A missing or wrong-version Clang frontend, malformed AST
JSON, invalid UTF-8 source, or unusable source location also fails closed.

A reference to a contracted-unavailable routine emits `MALBOLGE-LIBC-001` at
the selected source location. A reference to a forbidden external library
routine emits `MALBOLGE-LIBC-002`. Neither case proceeds to clang-tidy or later
lowering.

A declaration-only include does not by itself fail validation. The policy is on
library use, which permits shared source to include the stable guest headers
while still preventing accidental execution through host libraries.

## Verification

`tests/test_c_libc.py` proves:

- closed contract identity, ABI binding, routine sets, and header ownership;
- strict C23 wasm32 frontend compilation of both executable guest modules and
  the accepted source fixture;
- exact source-located diagnostics for unavailable allocation, unavailable
  transcendental `libm`, and forbidden host-process control;
- source-defined forbidden-name spellings are not false positives;
- declaration-only headers do not imply routine availability;
- the manual validator runs libc preflight before clang-tidy;
- on Windows, a pinned-Clang no-CRT executable exercises all 14 available
  routines and exits successfully;
- an independent 274-pattern rational differential locks exact binary64 math,
  while a separate 532-pattern arbitrary-precision integer-square-root
  differential locks canonical `sqrt`;
- memory/string objects have no undefined symbols; Windows math objects expose
  only the expected MSVC float marker, while wasm32 math objects expose only
  target stack machinery and no callable library dependency.

The no-CRT native harness is dependency evidence, not a claim that native
execution is guest execution. The routines are admitted because their actual
implementation is ordinary guest C that enters the same compiler pipeline as
user code; lane 8 remains responsible for the facilities that do not yet have a
guest implementation.

Repository validation remains `jig validate --root .` after focused Python,
C-frontend, native no-CRT, Ruff, and basedpyright checks pass.

## References

- [C Programming Language](../../../bibliography/languages/c.md)
- [Clang](../../../bibliography/tooling/clang.md)
- [Deterministic C Surface And Clang
  Tooling](../../adr/deterministic-c-surface-and-clang-tooling.md)
- [Compiler Pipeline And Guest
  Runtime](../../adr/compiler-pipeline-and-guest-runtime.md)
- [Deterministic C-to-Malbolge
  ABI](deterministic-c-to-malbolge-abi.md)

### Governing ADR Paths

- `docs/technical/adr/deterministic-c-surface-and-clang-tooling.md`
- `docs/technical/adr/compiler-pipeline-and-guest-runtime.md`
