# Ternary Lowering

## Purpose

Own deterministic lowering from validated typed compiler semantics into a
pre-layout ternary representation suited to later Malbolge layout and encoding.

## Ownership

This boundary is owned by `function:ternary-lowering`.

## Prohibitions

It must not parse C, import typed-IR implementation types, choose final target
addresses, encode Malbolge source, or substitute host computation for guest
semantics.

## Navigation

- `port-inbound/`: narrow semantic projection accepted from validated typed IR.
- `domain/`: deterministic pre-layout ternary values and source provenance.
- `application/`: fail-closed semantic lowering into target operations.
- `composition/`: canonical module topology for compiler assembly and tests.

## Status

The first executable slice lowers admitted no-argument `i32` constant-return
functions. Exact 32-bit bit patterns become fixed-width 21-trit scalars while
source, ABI, typed-IR version, source digest, and target-profile provenance are
preserved. Other valid typed-IR semantics fail explicitly. Layout, target
serialization, runtime intrinsic realization, and Malbolge encoding remain
open.
