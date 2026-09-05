# Guest Runtime

## Purpose

Own deterministic guest-runtime semantic cores that later lower into
Malbolge-oriented execution without host-defined computation.

## Ownership

This boundary is owned by `function:guest-runtime`.

## Prohibitions

It must not use host allocation, host standard streams, native pointer
serialization, or target-lowering implementation as semantic authority.

## Navigation

- `contract/`: versioned policy, interfaces, intrinsics, and format kernel.
- `domain/`: freestanding heap, byte-stream, frame, and format algorithms.

## Status

Active implementation. Version-one heap, hidden frame, byte-stream, startup,
and typed bounded-formatting semantics are implemented with guest-owned state
and no host callbacks. Exact `fabs`/`floor`/`ceil`/`trunc` plus canonical
nearest-ties-even `sqrt` guest math are implemented in the guest libc boundary.

C23 narrow-format tokenization, directive admission, canonical promoted-vararg
decoding, transactional dynamic-field/argument resolution, and scalar
`d/i/u/o/x/X/b/B/c/p/%` execution are implemented. `%p` formats the canonical
guest pointer encoding rather than a host address. A caller-proven live-object
memory view executes narrow `%s` reads and integer `%n` stores through the same
32-bit logical pointer encoding without exposing host pointer identity.

A separate integer-only floating boundary executes binary64 and binary128
`%a`/`%A` with normalized exact hexadecimal geometry and nearest-ties-even
rounding. Binary64 decimal work now also has a bounded exact magnitude
substrate:
finite bits become canonical decimal digits times a signed power of ten using
only 32-bit base-10000 limbs. Binary64 `%e`/`%E` now consumes that
representation
with decimal nearest-ties-even rounding and bounded scientific layout.

Binary64 `%f`/`%F` now uses the same exact decimal source, rounding the scaled
integer nearest-ties-even before placing the fixed decimal point. Source
`va_list` bridging remains compiler-lowering work. Binary64 `%g`/`%G`, decimal
binary128, wide-string formatting, and correctly-rounded transcendental math
remain open.
