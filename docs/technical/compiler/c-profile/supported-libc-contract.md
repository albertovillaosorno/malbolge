# Supported libc contract

- Status: Proposed
- Planning identity: `supported-libc-contract`
- Last reviewed: 2026-07-26

## Governing Decisions

- [Deterministic C Surface And Clang
  Tooling](../../adr/deterministic-c-surface-and-clang-tooling.md)
- [Compiler Pipeline And Guest
  Runtime](../../adr/compiler-pipeline-and-guest-runtime.md)

## Purpose

Define the guest C library surface: fixed-width integers, memory primitives,
byte streams, strings, allocation, formatting, and later higher-level routines
without hidden host shortcuts.

## Proposed Model

This record defines the contract that implementation must satisfy for
`supported-libc-contract`. The implementation may change internal representation
or language choices without changing the observable behavior, trust boundary, or
ownership rules stated by its governing decisions.

## Invariants

- The supported libc surface states exact C signatures and deterministic guest
  semantics and separates unsupported-today functionality from constructs
  forbidden by the language/ABI model.
- Accepted and rejected C fixtures exercise the boundary, and diagnostics
  identify the unsupported construct/profile requirement at source level.

## Failure Behavior

Unsupported or nondeterministic C is rejected at source locations rather than
lowered through host-dependent behavior.

## Verification

- Expected durable artifact surface: `tools/tidy/`, `libc/`, `runtime/`,
  `docs/technical/specification/`, `tests/tidy/`.
- Required evidence: accepted/rejected source fixtures, source-located
  diagnostics, and compiler/linter contract regression tests.

## Implementation Status

Not implemented. This proposed contract does not claim executable support yet.
