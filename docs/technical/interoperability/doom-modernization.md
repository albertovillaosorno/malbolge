# DOOM quality and modernization pass

## Status

Proposed

## Purpose

Normalize a user-supplied DOOM source tree before amalgamation. The quality pass
owns deterministic AST-level rewrites needed to satisfy the supported C profile,
repair demonstrable defects, modernize explicit platform boundaries, and produce
a stable multi-translation-unit tree for later aggregation.

## Scope

This document governs the following declared TODO scope:

- `doom/`
- `interop/algorithms/quality.rs`
- `interop/adapters/`
- `interop/algorithms/out/doom_fixed/`
- `tools/tidy/`

## Current Behavior

### Proposed Model

`quality.rs` reads the ignored user-owned source tree and emits a generated
normalized tree under `interop/algorithms/out/doom_fixed/`. Rewrites are driven
by Clang/AST semantics and the complete `tools/tidy` contract. Regex or other
textual rewriting is admitted only when the transformation is provably textual.

The pass may modernize video, input, timing, audio, game-data access, resolution,
frame pacing, and obvious source defects through explicit adapters while keeping
intentional behavior changes separately reviewable from semantics-preserving
normalization.

### Implementation Status

Not implemented. The repository does not claim that user-supplied DOOM source is
currently normalized or accepted by the target C profile.

## Invariants

- The input source tree under ignored `doom/` is never modified.
- Every required manual repair is converted into deterministic reusable logic or
  remains an explicit blocker.
- Blanket linter suppression is not an accepted modernization technique.
- Required upstream legal/provenance material is preserved.
- Native differential evidence follows every behavior-affecting rewrite.
- Amalgamation happens only after this pass has produced an accepted normalized
  multi-file tree.

## Failure Behavior

Unsupported language constructs, unresolved platform assumptions, failed
behavior comparisons, or missing legal/provenance requirements fail explicitly.
The pass leaves prior accepted generated stages inspectable rather than silently
publishing a partially transformed final artifact.

## Verification

- Deterministic source manifests identify every input/output translation unit.
- `tools/tidy` reports reach zero accepted diagnostics without blanket ignores.
- Differential native fixtures distinguish semantics-preserving rewrites from
  deliberate bug fixes or platform modernization.
- Adapter tests cover video, input, timing, audio, and game-data boundaries used
  by the normalized source tree.

## References

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
