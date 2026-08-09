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
and no host callbacks. Exact `fabs`/`floor`/`ceil`/`trunc` guest math is also
implemented in the guest libc boundary. Full printf parsing/varargs/floating
formatting and correctly-rounded inexact math remain open.
