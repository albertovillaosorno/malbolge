# Resident incremental compiler and WAL

## Status

Proposed

## Purpose

Define a native long-lived compiler service that keeps source, normalized IR,
dependency state, verified blocks, link plans, and reusable artifacts resident
in
RAM while persisting a deterministic write-ahead log for crash recovery. The
service exists to reduce rebuild latency without changing compiler semantics.

## Scope

This document governs the following declared TODO scope:

- `compiler/server/`
- `compiler/`
- `tests/compiler/`
- `benchmarks/compiler/`
- `runtime/`

## Current Behavior

### Proposed Model

The service maintains versioned source and IR identities plus a semantic
dependency graph. Edits invalidate the smallest sound closure of affected
frontend facts, IR nodes, verified blocks, link contracts, and emitted
artifacts.
A write-ahead log records deterministic state transitions needed to recover a
cache generation after interruption or reject it and rebuild from authoritative
source.

Fixed-width regions, unchanged byte counts, stable source offsets, and textual
hashes may be used as lookup accelerators only after semantic identities confirm
reuse is valid. They are never substitutes for parsing, typing, dependency, or
self-modification analysis.

### Implementation Status

Not implemented. This proposed contract does not claim a resident compiler,
hot reload, or zero-latency recompilation today.

## Invariants

- Resident and cold compilation of the same declared inputs are semantically
  equivalent and produce the same deterministic artifacts where byte identity is
  promised.
- WAL/cache state is rebuildable acceleration data, never source of truth.
- Recovery either reconstructs a verified cache generation or discards it; a
  partially replayed state cannot be accepted silently.
- Invalidation follows semantic dependencies through source, IR, layout, link,
  verifier, and self-modification contracts.
- Hot reload cannot mutate a running guest image unless the runtime can prove
  the
  patch preserves the declared guest-state transition contract.

## Failure Behavior

Corrupt, stale, incompatible, or partially replayed WAL/cache generations are
rejected and rebuilt. Unknown dependency edges invalidate conservatively rather
than reusing potentially stale artifacts. IPC or server failure must degrade to
a cold compiler path instead of changing accepted program semantics.

## Verification

- Differential tests compare cold and resident builds across single-function,
  cross-function, header, ABI, layout-sensitive, and mutation-sensitive edits.
- Crash/recovery fixtures interrupt WAL writes at deterministic boundaries and
  verify either exact recovery or safe rebuild.
- Benchmark evidence separates parse, invalidation, synthesis, verification,
  linking, serialization, and IPC costs.
- Tests demonstrate that equal length or equal position alone never authorizes
  semantic cache reuse.

## References

- [Compiler Pipeline And Guest
  Runtime](../adr/compiler-pipeline-and-guest-runtime.md)
- [Verification Trust Boundary](../adr/verification-trust-boundary.md)
- [State-aware Malbolge linker](state-aware-malbolge-linker.md)
- [C-level source mapping and
  debugging](source-mapping-debugging.md)

### Governing ADR Paths

- `docs/technical/adr/compiler-pipeline-and-guest-runtime.md`
- `docs/technical/adr/verification-trust-boundary.md`
