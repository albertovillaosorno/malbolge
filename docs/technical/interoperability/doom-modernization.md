# DOOM quality and modernization pass

## Status

Active implementation

## Purpose

Normalize a user-supplied DOOM source tree before amalgamation. The quality pass
owns deterministic AST-level rewrites needed to satisfy the supported C profile,
repair demonstrable defects, modernize explicit platform boundaries, and produce
a stable multi-translation-unit tree for later aggregation.

## Scope

This document governs the following declared TODO scope:

- `doom/`
- `interop/algorithms/quality/`
- `interop/adapters/`
- `interop/algorithms/quality/out/doom_fixed/`
- `tools/tidy/`

## Current Behavior

### Proposed Model

`quality/main.rs` ultimately reads the admitted user-owned source tree and emits a generated
normalized tree under `interop/algorithms/quality/out/doom_fixed/`. Rewrites are driven
by Clang/AST semantics and the complete `tools/tidy` contract. Regex or other
textual rewriting is admitted only when the transformation is provably textual.

The pass may modernize video, input, timing, audio, game-data access, resolution,
frame pacing, and obvious source defects through explicit adapters while keeping
intentional behavior changes separately reviewable from semantics-preserving
normalization.

### Implementation Status

The quality boundary and local development/evidence workflow are active, but the
reusable AST transformation engine is not complete. Repository-root `doom/` is
the untouched local baseline. The ignored `interop/algorithms/quality/in/doom/`
tree is currently a manually modernized development oracle used to discover
transformations that must later be encoded in `quality/main.rs` and reproduced
into `out/doom_fixed/`.

`interop/algorithms/quality/comparison/generate.py` measures both local corpora
with pinned LLVM 22.1.8 quality gates and emits aggregate versioned evidence. It
records source and asset SHA-256 identities and re-measures each corpus after
long-running validation, failing closed rather than publishing mixed-revision
evidence when a live tree changes. The current coherent snapshot reduces unique
quality findings from 143,662 to 38,462. This is development evidence only; the
normalized tree is not yet accepted by the full guest-C profile.

## Invariants

- The input source tree under ignored `doom/` is never modified.
- Every required manual repair is converted into deterministic reusable logic or
  remains an explicit blocker.
- Blanket linter suppression is not an accepted modernization technique.
- Required upstream legal/provenance material is preserved.
- Native differential evidence follows every behavior-affecting rewrite.
- Amalgamation, when requested, consumes only an accepted normalized multi-file
  tree. It remains optional rather than becoming a prerequisite for multi-file
  guest-C validation or compilation.

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
- `interop/algorithms/quality/comparison/{report.tex,metrics.json}` retains a
  compact aggregate progress snapshot with exact source/asset identities; its
  generator refuses mixed-revision live-corpus measurements.
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
