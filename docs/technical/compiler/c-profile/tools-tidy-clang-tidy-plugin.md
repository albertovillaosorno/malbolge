# tools/tidy clang-tidy plugin

## Status

Active implementation

## Purpose

Build `tools/tidy/` as an out-of-tree clang-tidy plugin compiled against the
pinned LLVM version. Add Malbolge checks without forking Clang or weakening the
existing clang-tidy baseline.

## Scope

This document governs the following declared TODO scope:

- `tools/tidy/`
- `scripts/validate/`
- `libc/`
- `runtime/`
- `docs/technical/specification/`
- `tests/tidy/`

## Current Behavior

### Proposed Model

This record defines the contract that implementation must satisfy for
`tools-tidy-clang-tidy-plugin`. The implementation may change internal
representation or language choices without changing the observable behavior,
trust boundary, or ownership rules stated by its governing decisions.

### Implementation Status

A manual root validator and stock-clang bootstrap profile are executable. The
out-of-tree `malbolge-*` plugin remains unfinished, so a bootstrap-clean verdict
does not yet claim complete C-to-Malbolge lowerability.

## Invariants

- The out-of-tree plugin loads against the pinned LLVM version, registers only
  documented `malbolge-*` checks, and emits deterministic source-located
  diagnostics without weakening ordinary clang-tidy checks.
- Guest-C validation is opt-in for explicitly selected translation units;
  arbitrary
  repository C is never enrolled by extension, inherited
  `.jig/lang/cpp/.clang-tidy`, or magic
  source comments. An explicitly passed directory named `doom` is the sole
  recursive convenience and remains an explicit caller action.
- Accepted and rejected C fixtures exercise the boundary, and diagnostics
  identify the unsupported construct/profile requirement at source level.
- Rust fixtures/tests exist to develop and regress this profile; explicit
  `tools/tidy` invocation remains the user-facing compatibility decision.

## Failure Behavior

Unsupported or nondeterministic C is rejected at source locations rather than
lowered through host-dependent behavior.

## Verification

- Expected durable artifact surface: `tools/tidy/`, `scripts/validate/`,
  `libc/`,
  `runtime/`,
  `docs/technical/specification/`, `tests/tidy/`.
- Required evidence: accepted/rejected source fixtures, source-located
  diagnostics, and compiler/linter contract regression tests.
- Prerequisite completion evidence: `deterministic-c-to-malbolge-abi`,
  `jig-repository-governance`.
## References

- [Deterministic C Surface And Clang
  Tooling](../../adr/deterministic-c-surface-and-clang-tooling.md)
- [Compiler Pipeline And Guest
  Runtime](../../adr/compiler-pipeline-and-guest-runtime.md)

### Governing ADR Paths

- `docs/technical/adr/deterministic-c-surface-and-clang-tooling.md`
- `docs/technical/adr/compiler-pipeline-and-guest-runtime.md`
