# Typed Compiler IR

## Purpose

Own the portable typed control-flow IR between normalized C and target lowering.

## Ownership

This boundary is owned by `function:typed-ir`.

## Prohibitions

It must not inherit LLVM IR syntax, native data layout, or Malbolge encoding.

## Navigation

- `contract/`: closed version-one grammar and canonical identity rules.
- `domain/`: portable IDs, types, instructions, control flow, and module values.
- `application/`: admission, frontend lowering, proof checks, and encoding.
- `composition/`: canonical product module topology.

## Status

Implemented version one. The safe Rust model, SSA/CFG/type/proof validator,
finite guest object layout, automatic storage, direct/indirect call semantics,
validation-gated canonical bytes, deterministic debug identity, and normalized
frontend handoff are implemented. Unsupported frontend semantic shapes fail
closed; full accepted-C coverage is owned by the later tools/tidy lowerability
contract rather than weakening this IR boundary.
