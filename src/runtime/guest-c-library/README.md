# Guest C Library Function Boundary

## Purpose

This function owns the guest-visible C library contract and implementations
that execute as ordinary guest code. It separates executable routines from
contracted facilities whose runtime implementation belongs to a later lane.

## Ownership

- Owns: Guest libc declarations and repository-owned guest C implementations.
- Authority: `function.yml` plus the canonical `c-libc-v1.json` specification.

## Prohibitions

- Must not: Resolve guest library calls through host libc or host `libm`.
- Must not: Treat native debug adapters as guest-runtime conformance evidence.

## Navigation

- `contract/include/`: guest headers backed by executable guest code.
- `domain/`: deterministic freestanding implementations of admitted routines.
