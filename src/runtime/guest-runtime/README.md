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
`d/i/u/o/x/X/b/B/c/p/%` execution are implemented, with `%p` formatting the
canonical guest pointer encoding rather than a host address. Source `va_list`
bridging remains compiler-lowering work; guest-memory and floating formatting
plus
correctly-rounded transcendental math remain open.
