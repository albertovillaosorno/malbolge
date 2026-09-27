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
- `composition/`: canonical module topology and verified progress-sidecar
  orchestration.
- `application/`: admission, frontend lowering, checkpoint restoration,
  fresh-or-resumed stage entry, proof checks, and encoding.

## Status

Implemented version one. The safe Rust model, SSA/CFG/type/proof validator,
finite guest object layout, automatic storage, direct/indirect call semantics,
validation-gated canonical bytes, deterministic debug identity, one
fresh-or-resumed normalized-frontend/typed-IR stage handoff, and verified
progress-sidecar checkpoint adaptation are implemented. Unsupported frontend
semantic shapes fail closed; full accepted-C coverage is owned by the later
tools/tidy lowerability
contract rather than weakening this IR boundary.
