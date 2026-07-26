# Explicit native-tier execution controls

- Status: Proposed
- Planning identity: `explicit-native-tier-execution-controls`
- Last reviewed: 2026-07-26

## Governing Decisions

- [Tiered Native Execution](../adr/tiered-native-execution.md)
- [Verification Trust Boundary](../adr/verification-trust-boundary.md)

## Purpose

Expose independent `--no-jit` and `--no-aot` runtime controls plus an
`--interpreter-only` shorthand equivalent to disabling both native compilation
tiers and native-code cache reuse. Default execution may use AOT, JIT, graph
optimization, and interpreter fallback, but interpreter-only mode must execute
the Malbolge machine directly without generating host machine code. Use these
modes for differential correctness checks and honest measurements of pure VM,
AOT-only, JIT-only, and fully tiered execution.

## Proposed Model

This record defines the contract that implementation must satisfy for
`explicit-native-tier-execution-controls`. The implementation may change
internal representation or language choices without changing the observable
behavior, trust boundary, or ownership rules stated by its governing decisions.

## Invariants

- `--no-jit`, `--no-aot`, and `--interpreter-only` have independently tested
  behavior; interpreter-only performs no native generation or native-cache
  reuse.
- Observable state, I/O, termination, and diagnostics match the declared
  semantic profile across positive, boundary, and adversarial fixtures.

## Failure Behavior

Invalid programs, unsupported profiles, or broken native assumptions fail
deterministically without changing guest-visible state silently.

## Verification

- Expected durable artifact surface: `vm/`, `execution/`, `tests/vm/`,
  `benchmarks/interpreter/`.
- Required evidence: semantic fixtures, state/I/O traces where diagnostic, and
  differential results against the applicable oracle/reference implementation.

## Implementation Status

Not implemented. This proposed contract does not claim executable support yet.
