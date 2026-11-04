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
progress-sidecar checkpoint adaptation are implemented. Source-bound resume
also requires the exact two-entry type table emitted by each supported
frontend slice (i32/function for integer returns; u8/void-function for the
explicit effect-free void return). A valid checkpoint with extra unused type
entries is not evidence of equivalent fresh lowering. Fresh and source-bound
frontend admission reject empty integer-literal spans, literals outside their
owning return statements, overlapping distinct C function definitions, and
mixed void/integer source projections.

The narrow `fn()->void` frontend projection lowers a no-argument function
containing one explicit `return;` to a single empty typed block ending in
`Return { value: None }`. Source-bound checkpoint recovery checks the exact
function/return spans, function ABI, empty instructions and type identities.
The resulting canonical MCTI is independently admitted by the opt-in
`malbolge_layout --empty-void --typed-file` pathway and can execute as a
verified two-step no-op/halt program. `tests/compiler_void_projection_vm.rs`
exercises the projection, MCTI codec, compiled capsule and real VM runner.
That fixture builds a **typed normalized projection**, not the native Clang
frontend JSON: JSON-to-typed projection adaptation, physical C-source compiler
composition, arbitrary effects, and a C process-return ABI remain unsupported.
Unsupported frontend semantic shapes fail closed; full accepted-C coverage
is owned by the later tools/tidy lowerability contract rather than weakening
this IR boundary.
