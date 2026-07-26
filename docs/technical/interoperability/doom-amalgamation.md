# User-supplied DOOM source interoperability generator

- Status: Proposed
- Planning identity: `user-supplied-doom-source-interoperability-generator`
- Last reviewed: 2026-07-26

## Governing Decisions

- [Deterministic C Surface And Clang
  Tooling](../adr/deterministic-c-surface-and-clang-tooling.md)
- [Compiler Pipeline And Guest
  Runtime](../adr/compiler-pipeline-and-guest-runtime.md)
- [Legal Research And Repository
  Boundary](../../legal/adr/legal-research-and-repository-boundary.md)

## Purpose

Consume a user-supplied lawful DOOM source tree from the ignored root `doom/`
directory and use `interop/algorithms/amalgamate.rs` to construct the canonical
intermediate `interop/algorithms/out/doom_amalgamated.c`. Resolve translation-
unit boundaries, internal-linkage collisions, preprocessing environments,
includes, declarations, and provenance through pinned Clang rather than unsafe
textual concatenation. Differentially compare the original native build with the
amalgamated build before admitting the artifact to later transformation. The
repository does not redistribute the user-supplied source or game data, and
generated material keeps its applicable upstream license and provenance.

## Proposed Model

This record defines the contract that implementation must satisfy for
`user-supplied-doom-source-interoperability-generator`. The implementation may
change internal representation or language choices without changing the
observable behavior, trust boundary, or ownership rules stated by its governing
decisions.

## Invariants

- The source tree under ignored `doom/` is never modified; `amalgamate.rs`
  writes `interop/algorithms/out/doom_amalgamated.c` deterministically and
  preserves required provenance.
- The end-to-end fixture demonstrates the intended behavior from admitted
  source/input through the actual generated/executed Malbolge path.

## Failure Behavior

Missing external inputs or unmet target capabilities fail explicitly;
demonstrations may not substitute host logic for guest behavior.

## Verification

- Expected durable artifact surface: `doom/`,
  `interop/algorithms/amalgamate.rs`, `interop/algorithms/out/`,
  `tests/applications/doom/out/`.
- Required evidence: reproducible build/run commands, expected outputs or
  interaction traces, artifact hashes, and end-to-end verification.

## Implementation Status

Not implemented. This proposed contract does not claim executable support yet.
