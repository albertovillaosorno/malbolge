# Guest runtime and allocator

## Status

Active implementation

## Purpose

Implement startup, calling convention, frames, allocation, streams, integer
helpers, strings, deterministic math helpers, scheduling primitives, and other
runtime facilities as code that ultimately executes under Malbolge semantics.

## Scope

This document governs the following declared TODO scope:

- `tools/tidy/`
- `src/runtime/`
- `docs/technical/specification/`
- `tests/tidy/`
- `tests/runtime/`
- `tests/test_guest_runtime_c.py`

## Current Behavior

### Versioned runtime authority

`src/runtime/guest-runtime/contract/guest-runtime-v1.json` is the
runtime-specific
version-one authority layered on top of the existing C ABI and target profile.
It freezes status identities, guest-heap metadata geometry/policy, startup
binding behavior, the canonical-frame authority reference, byte-I/O intrinsic
symbols, and the prohibition on host fallback. It does not duplicate the full C
ABI or target profile; tests require its C projection to match those
authorities.

`tests/test_guest_runtime_authority.py` checks the C status/heap constants and
metadata offsets against this runtime contract, frame fields against
`c-abi-v1.json`, EOF/alignment against the selected `malbolge.json` profile/ABI,
and confirms that implemented allocation/byte wrappers remain source-unavailable
until their integration gates complete.

### Implemented runtime core

`src/runtime/guest-runtime/` is a governed C function that owns the first stable
lane-8 runtime semantics. `contract/guest_runtime.h` defines fixed status
values,
16-byte heap alignment/header geometry, the current profile EOF word, a caller-
owned heap state, and byte-stream conversion entry points. The contract uses
fixed `uint32_t` extents so guest semantics do not inherit native `size_t` or
pointer serialization.

The heap domain is a deterministic first-fit arena allocator. Every block begins
with a canonical 16-byte little-endian header containing span, requested extent,
allocation state, and a zero reserved word. Allocation uses checked 32-bit
extent
arithmetic and 16-byte payload alignment, splits useful free remainders,
coalesces adjacent free blocks, and trims a free tail. Every public heap
operation validates the complete canonical block chain before mutation, so even
a corrupt later header prevents an earlier allocation/free/resize from changing
state or publishing a result. Zero-size allocation has
the implementation-defined C choice of deterministic null. Zeroed allocation
checks multiplication overflow before publication. Resize preserves the old
allocation on exhaustion and either changes the block in place or copies the
lesser of old/new requested bytes before releasing the old block. A nonnull
zero-size resize is outside this contracted path because C23 makes that call
undefined; the core reports an invalid request rather than defining guest C
semantics for undefined behavior.

The frame domain consumes the canonical `malbolge-c32-v1` hidden call-frame
layout without inventing another runtime ABI. It encodes/decodes the exact
32-byte little-endian field sequence, requires a 16-byte-aligned frame extent of
at least 32 bytes, requires the ABI-mandated argument-block pointer, and rejects
nonzero version-one flags. Encoding validates and stages bytes before publishing
them; decoding stages all fields and validates before mutating its output.
Native return addresses and native stack metadata never enter this codec.

The byte-stream domain has no host I/O. Current-profile input words `0..255` map
to C `int` values, EOF word `4,782,968` maps to `-1`, impossible intermediate
words are rejected, and output is the low eight bits of the supplied C value.

Guest startup now has an explicit one-time heap-binding domain. Allocation
requests before binding fail as `NOT_INITIALIZED`; an invalid bind leaves state
uninitialized; the first successful bind initializes/zeroes the guest arena; and
later rebind attempts fail as `ALREADY_INITIALIZED`. The four public allocation
wrappers (`malloc`, `calloc`, `realloc`, and `free`) delegate only to these
startup-bound guest-runtime entry points. Their wasm32 source compiles under the
strict guest profile and their native relocatable object has exactly the four
expected guest-runtime undefined symbols and no host allocation dependency.

These allocation functions intentionally remain *unavailable* in the canonical
`malbolge-libc-v1` authority until compiler-generated startup proves the heap
bind occurs before user code.

Byte I/O now has stable declaration-only compiler intrinsic identities and
public `getchar`/`putchar` wrapper source. The input wrapper invokes the
intrinsic word, uses the pure profile-word decoder, and returns byte-or-`EOF`;
output reduces the C value to its low eight bits, invokes the output-byte
intrinsic, and returns the emitted unsigned byte. The selected profile output
effect is infallible, so its `putchar` specialization always returns that
emitted byte. Independent test intrinsics execute these wrappers without host
streams. The production object depends only on the two intrinsic symbols plus
the pure mapping helpers. The routines intentionally remain
*unavailable* until `ternary-machine-lowering` proves the intrinsic identities
realize the selected-profile `/` and `<` operations.

### Typed bounded-formatting kernel

`src/runtime/guest-runtime/contract/guest_format.h` and `domain/format.c`
implement an internal, typed formatting kernel below the public printf family.
The kernel owns exact signed/unsigned integer conversion for bases 2, 8, 10,
and 16, sign/prefix/width/precision padding, narrow-string precision, character
fields, bounded destination writes, final-null reservation, and an exact
would-have-written `u32` count. Large discarded width/precision is accounted in
constant work per emitted segment rather than by looping over bytes that cannot
fit the destination.

The kernel deliberately does not parse a format string, consume `va_list`, or
format floating values. The C23 `snprintf`/`vsnprintf` contract covers the full
formatted-output grammar and requires the same would-have-written result even
under truncation. Therefore this kernel is implementation substrate only;
`snprintf` and `vsnprintf` remain contracted-unavailable until parser, guest
variadic decoding, all admitted conversions, and floating formatting are
complete.

Independent C vectors lock decimal/hex/octal/binary integer output,
INT64_MIN, alternate prefixes, precision-versus-zero padding, left/right width,
string precision, character fields, truncation, null-capacity behavior,
count-overflow rejection, and corrupted-sink rejection. Windows i686/x64/ARM64
objects have no undefined symbols; wasm32 exposes only target stack machinery.
The same vectors pass pinned ASan/UBSan and path-sensitive Clang analysis.

### Exact binary64 math

`src/runtime/guest-c-library/domain/math_exact.c` implements `fabs`, `floor`,
`ceil`, and `trunc` directly from the ABI-fixed binary64 representation. WG14
records these operations as exact and independent of the current rounding
mode. The implementation uses representation-level masks only: signed zeros,
subnormals, integral values, and infinities retain their required semantics,
and every NaN publishes the ABI canonical quiet payload-zero NaN.

The no-CRT guest-libc harness locks exact result bits for positive/negative
zero, fractional boundaries, minimum subnormals, infinities, quiet NaNs, and
signaling NaNs. A separate fixed-seed 274-pattern differential reconstructs each
finite input as an exact rational and independently derives the expected result
bits. The wasm32 guest object has no library dependency beyond target
stack machinery at unoptimized codegen. Windows MSVC objects expose only the
compiler's `_fltused` marker; the test harness supplies that marker without
adding a host `libm` implementation.

`fabs`, `floor`, `ceil`, and `trunc` are therefore executable in
`malbolge-libc-v1`. `sqrt`, `sin`, `cos`, and `atan2` remain unavailable until
correctly-rounded guest algorithms satisfy their stronger contracts.

Version one needs no separate guest scheduler or ordinary-integer-helper API:
integer operations are explicit typed-IR semantics for lane-9 lowering, and the
selected target profile is sequential with no guest thread surface. Allocation
startup binding and byte-I/O intrinsic realization are likewise lane-9 target
work over the stable identities defined here. Remaining lane-8 algorithm work
is the complete public printf parser/guest-varargs/floating formatter plus
correctly-rounded `sqrt`, `sin`, `cos`, and `atan2`.

## Invariants

- Allocation, streams, arithmetic/math helpers, calling-convention support,
  and other runtime facilities have deterministic guest-owned semantics and
  freestanding implementations. Hidden host callbacks cannot define guest
  computation.
- Fundamental compiler intrinsics have explicit versioned guest-runtime
  contracts. Native debug adapters may mirror them but cannot define them.
- Executable ternary/Malbolge realization is owned by the downstream
  `ternary-machine-lowering` stage, which consumes these runtime identities
  unchanged. This separation preserves the eventual Malbolge-semantics invariant
  without making lane 8 depend on lane 9.
- Accepted and rejected C fixtures exercise the boundary, and diagnostics
  identify the unsupported construct/profile requirement at source level.

## Failure Behavior

Unsupported or nondeterministic C is rejected at source locations rather than
lowered through host-dependent behavior.

## Verification

- Expected durable artifact surface: `tools/tidy/`, `src/runtime/`,
  `docs/technical/specification/`, `tests/tidy/`, `tests/runtime/`, and
  `tests/test_guest_runtime_c.py`.
- Required evidence: accepted/rejected source fixtures, source-located
  diagnostics, runtime semantic/conformance fixtures, and compiler/runtime
  regression tests that prove guest computation has no host-defined fallback.
- Current executable evidence: `tests/test_guest_runtime_c.py` compiles strict
  C23 conformance vectors for i686, x86-64, and AArch64 Windows ABIs and
  executes
  them natively. It locks frame wire bytes, heap metadata bytes/alignment,
  allocation lifecycle, zeroing/overflow, resize/tail-growth preservation,
  corruption rejection including late-corruption nonmutation, and byte
  mapping. A deterministic 4,000-operation
  allocator stress sequence independently parses the raw heap chain after every
  operation. The same vectors pass pinned ASan/UBSan and Clang static analysis.
  Freestanding runtime objects are checked under all three reviewed Windows ABIs
  so compiler-injected library helpers cannot silently enter the runtime core.
- Dependency boundary: executable ternary/Malbolge lowering is intentionally
  downstream under `ternary-machine-lowering`; this contract supplies its stable
  runtime semantic identities and implementation inputs.
- Prerequisite completion evidence: `supported-libc-contract`,
  `safe-rust-malbolge-vm`.
## References

- [Deterministic C Surface And Clang
  Tooling](../../adr/deterministic-c-surface-and-clang-tooling.md)
- [Compiler Pipeline And Guest
  Runtime](../../adr/compiler-pipeline-and-guest-runtime.md)

### Governing ADR Paths

- `docs/technical/adr/deterministic-c-surface-and-clang-tooling.md`
- `docs/technical/adr/compiler-pipeline-and-guest-runtime.md`
