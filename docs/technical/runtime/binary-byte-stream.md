# Deterministic binary byte-stream runtime

- Status: Proposed
- Planning identity: `deterministic-binary-byte-stream-runtime`
- Last reviewed: 2026-07-26

## Governing Decisions

- [Compiler Pipeline And Guest
  Runtime](../adr/compiler-pipeline-and-guest-runtime.md)
- [Verification Trust Boundary](../adr/verification-trust-boundary.md)

## Purpose

Prove generated programs can consume and emit arbitrary binary byte streams
without host-side format logic, creating the foundation for real deterministic
file transformers.

## Proposed Model

This record defines the contract that implementation must satisfy for
`deterministic-binary-byte-stream-runtime`. The implementation may change
internal representation or language choices without changing the observable
behavior, trust boundary, or ownership rules stated by its governing decisions.

## Invariants

- Guest programs can read and emit all byte values including NUL and arbitrary
  binary sequences with no host-side format parser/writer logic and
  deterministic stream termination/error rules.
- The end-to-end fixture demonstrates the intended behavior from admitted
  source/input through the actual generated/executed Malbolge path.

## Failure Behavior

Missing external inputs or unmet target capabilities fail explicitly;
demonstrations may not substitute host logic for guest behavior.

## Verification

- Expected durable artifact surface: `docs/technical/examples/`,
  `tests/applications/`, `benchmarks/applications/`, `runtime/`.
- Required evidence: reproducible build/run commands, expected outputs or
  interaction traces, artifact hashes, and end-to-end verification.

## Implementation Status

Not implemented. This proposed contract does not claim executable support yet.
