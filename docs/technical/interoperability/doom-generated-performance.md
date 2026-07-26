# DOOM playable generated-code performance

## Status

Proposed

## Purpose

Optimize lowering, block selection, guest runtime, VM execution, JIT paths, and
accelerator-assisted compilation until the user-supplied DOOM interoperability
pipeline produces a `.malbolge` build that is genuinely interactive and playable
under the modern runtime. Measure compile latency, frame pacing, input latency,
VM instructions per game tick, memory footprint, and generated-code size rather
than declaring success merely because the program eventually runs. Preserve the
same game semantics while optimizing; performance-specific substitutions require
explicit equivalence evidence.

## Scope

This document governs the following declared TODO scope:

- `tests/applications/doom/`
- `benchmarks/doom/`
- `compiler/`
- `execution/`
- `accelerator/`

## Current Behavior

### Proposed Model

This record defines the contract that implementation must satisfy for
`doom-playable-generated-code-performance`. The implementation may change
internal representation or language choices without changing the observable
behavior, trust boundary, or ownership rules stated by its governing decisions.

### Implementation Status

Not implemented. This proposed contract does not claim executable support yet.

## Invariants

- Success requires an objectively documented interactive/playability budget for
  the generated `.malbolge`, with native C behavior retained as the comparison
  oracle and no host-side game logic substitution.
- The end-to-end fixture demonstrates the intended behavior from admitted
  source/input through the actual generated/executed Malbolge path.
- Performance conclusions use equivalent workloads and report raw-sample
  provenance, resource budgets, dispersion/uncertainty, and failure/success
  behavior rather than only a best-case number.

## Failure Behavior

Missing external inputs or unmet target capabilities fail explicitly;
demonstrations may not substitute host logic for guest behavior.

## Verification

- Expected durable artifact surface: `tests/applications/doom/`,
  `benchmarks/doom/`, `compiler/`, `execution/`, `accelerator/`.
- Required evidence: reproducible build/run commands, expected outputs or
  interaction traces, artifact hashes, and end-to-end verification.
- Prerequisite completion evidence:
  `user-supplied-doom-source-interoperability-generator`,
  `malbolge-layout-and-encoding-backend`,
  `explicit-native-tier-execution-controls`, `deterministic-cpu-optimizer`.
- Performance evidence pending: raw measurements plus a reproducible
  scaling/statistical summary tied to exact workload and hardware/software
  identity.
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
