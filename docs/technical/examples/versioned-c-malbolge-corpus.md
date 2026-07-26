# Versioned C and Malbolge example corpus

- Status: Proposed
- Planning identity: `versioned-c-and-malbolge-example-corpus`
- Last reviewed: 2026-07-26

## Governing Decisions

- [Compiler Pipeline And Guest
  Runtime](../adr/compiler-pipeline-and-guest-runtime.md)
- [Verification Trust Boundary](../adr/verification-trust-boundary.md)

## Purpose

Publish intentionally selected project-owned examples under
`docs/technical/examples/` with paired `.c` and `.malbolge` artifacts. Include
small teaching examples plus representative fixed instances drawn from the
parametric challenge corpus. Each pair identifies challenge/source identity,
target profile, compiler identity, input/output contract, reproducible build
command, expected behavior, and verification evidence. Documentation examples
are versioned deliberately; normal benchmark outputs remain local under their
owning `out/` directories.

## Proposed Model

This record defines the contract that implementation must satisfy for
`versioned-c-and-malbolge-example-corpus`. The implementation may change
internal representation or language choices without changing the observable
behavior, trust boundary, or ownership rules stated by its governing decisions.

## Invariants

- Every committed `.c`/`.malbolge` pair is an intentional documentation artifact
  with compiler/profile identity, reproducible command, expected behavior, and
  verification hash/evidence.
- The end-to-end fixture demonstrates the intended behavior from admitted
  source/input through the actual generated/executed Malbolge path.

## Failure Behavior

Missing external inputs or unmet target capabilities fail explicitly;
demonstrations may not substitute host logic for guest behavior.

## Verification

- Expected durable artifact surface: `docs/technical/examples/`,
  `tests/golden/`, `compiler/`.
- Required evidence: reproducible build/run commands, expected outputs or
  interaction traces, artifact hashes, and end-to-end verification.

## Implementation Status

Not implemented. This proposed contract does not claim executable support yet.
