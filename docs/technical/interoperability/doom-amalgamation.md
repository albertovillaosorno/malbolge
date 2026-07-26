# User-supplied DOOM source interoperability generator

## Status

Proposed

## Purpose

Amalgamate the already normalized generated DOOM source tree into one canonical C
translation artifact without changing native semantics. The generator exists to
make later compiler/tooling experiments consume one deterministic source artifact
without pretending that plain file concatenation preserves C translation-unit
behavior.

## Scope

This document governs the following declared TODO scope:

- `interop/algorithms/amalgamate/main.rs`
- `interop/algorithms/quality/out/doom_fixed/`
- `interop/algorithms/amalgamate/out/doom_amalgamated.c`
- `tests/applications/doom/out/doom.c`

## Current Behavior

### Proposed Model

`amalgamate/main.rs` consumes the normalized multi-file tree produced by the quality
pass. Pinned Clang preprocessing/AST information provides translation-unit,
linkage, macro, declaration, and provenance context. The algorithm deterministically
renames or materializes only what is necessary to preserve semantics when the
translation units become one file.

The final admitted source artifact is `doom_amalgamated.c`; the end-to-end test
receives a byte-identical copy named `doom.c` under its ignored output directory.

### Implementation Status

Not implemented. The repository does not claim that normalized DOOM sources can
currently be amalgamated correctly.

## Invariants

- The input is the generated normalized tree, not the original user-owned tree.
- Amalgamation is AST/preprocessor aware where C scope, types, macros, linkage, or
  conditional compilation affect meaning.
- Internal-linkage collisions are resolved deterministically with provenance.
- Required upstream licensing/provenance information survives aggregation.
- Manual source edits are not part of the accepted reproducible pipeline.

## Failure Behavior

Unresolved translation-unit semantics, ambiguous preprocessing state, failed
native differential checks, or provenance loss fail explicitly and leave the
last accepted generated stage intact.

## Verification

- Repeated aggregation from the same normalized tree yields byte-identical output.
- Native differential tests compare the normalized multi-file build with the
  amalgamated build over the strongest practical corpus and state observations.
- Symbol/linkage manifests prove collision handling and deterministic renaming.
- The test `doom.c` copy is byte-identical to the accepted amalgamated artifact.

## References

- [DOOM quality and modernization pass](doom-modernization.md)
- [Deterministic C Surface And Clang
  Tooling](../adr/deterministic-c-surface-and-clang-tooling.md)
- [Compiler Pipeline And Guest
  Runtime](../adr/compiler-pipeline-and-guest-runtime.md)
- [Legal Research And Repository
  Boundary](../../legal/adr/legal-research-and-repository-boundary.md)

### Governing ADR Paths

- `docs/technical/adr/deterministic-c-surface-and-clang-tooling.md`
- `docs/technical/adr/compiler-pipeline-and-guest-runtime.md`
- `docs/legal/adr/legal-research-and-repository-boundary.md`