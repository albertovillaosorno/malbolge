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
rounding. Decimal `%e/%E/%f/%F/%g/%G` now covers both widths from bounded exact
magnitudes represented as canonical decimal digits times a signed power of ten.
Binary64 keeps its 192-limb scratch; binary128 uses 2,891 base-10000 limbs and
at most 11,563 exact digits.

Both widths share decimal nearest-ties-even rounding and bounded publication.
Fixed style rounds the scaled integer before point placement. General style
rounds significant digits first, selects fixed or scientific layout from the
rounded exponent, and trims trailing fractional zeroes unless `#` preserves
them.

Source `va_list` bridging remains compiler-lowering work. Wide-string
formatting and correctly-rounded transcendental math remain open.
