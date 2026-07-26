# DOOM quality and modernization pass

- Status: Proposed
- Planning identity: `doom-quality-and-modernization-pass`
- Last reviewed: 2026-07-26

## Governing Decisions

- [Deterministic C Surface And Clang
  Tooling](../adr/deterministic-c-surface-and-clang-tooling.md)
- [Compiler Pipeline And Guest
  Runtime](../adr/compiler-pipeline-and-guest-runtime.md)
- [Legal Research And Repository
  Boundary](../../legal/adr/legal-research-and-repository-boundary.md)

## Purpose

Use `interop/algorithms/quality.rs` to transform
`interop/algorithms/out/doom_amalgamated.c` into the clean modern-host artifact
`interop/algorithms/out/doom_fixed.c`, which must pass the complete `malbolge-
tidy` contract without suppressions. Convert repeated linter failures into
reusable AST transformations; replace unavailable legacy platform integration
through explicit adapters for video, input, timing, audio, and game-data
access; support scalable modern resolutions and a measured 60 FPS target where
game semantics permit it; repair demonstrable source defects; remove
nonessential inherited comments and stale notes while preserving required legal
provenance; and regenerate concise project-quality comments where useful. After
validation, copy `doom_fixed.c` byte-for-byte to
`tests/applications/doom/out/doom.c` for the end-to-end test harness.
Differential native tests follow every behavior-affecting rewrite. Regex is
allowed only for transformations proven to be purely textual; user-owned DOOM
data remains external.

## Proposed Model

This record defines the contract that implementation must satisfy for
`doom-quality-and-modernization-pass`. The implementation may change internal
representation or language choices without changing the observable behavior,
trust boundary, or ownership rules stated by its governing decisions.

## Invariants

- `quality.rs` writes `doom_fixed.c`, obtains full linter/differential
  acceptance, then copies it byte-for-byte to
  `tests/applications/doom/out/doom.c`; no blanket lint suppression is allowed.
- The end-to-end fixture demonstrates the intended behavior from admitted
  source/input through the actual generated/executed Malbolge path.

## Failure Behavior

Missing external inputs or unmet target capabilities fail explicitly;
demonstrations may not substitute host logic for guest behavior.

## Verification

- Expected durable artifact surface: `interop/algorithms/quality.rs`,
  `interop/adapters/`, `interop/algorithms/out/`,
  `tests/applications/doom/out/`, `tools/tidy/`.
- Required evidence: reproducible build/run commands, expected outputs or
  interaction traces, artifact hashes, and end-to-end verification.

## Implementation Status

Not implemented. This proposed contract does not claim executable support yet.
