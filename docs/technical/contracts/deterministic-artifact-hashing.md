# Deterministic cross-backend artifact hashing

## Status

Proposed

## Intent

Require exact artifact hashes for deterministic replay of the *same*
versioned compiler, selected algorithm/seed/configuration, source/profile and
backend policy. Different valid optimizers or CPU/CUDA candidate order may
produce different bytes and hashes, but must satisfy the same independently
checked source semantics.

## Contract

### Proposed Model

This record defines the contract that implementation must satisfy for
`deterministic-cross-backend-artifact-hashing`. The implementation may change
internal representation or language choices without changing the observable
behavior, trust boundary, or ownership rules stated by its governing decisions.

### Finite Acceptance Boundary (2026-11-16)

P4 uses two identical CPU compilations, one alternate independently accepted
optimizer artifact and one rejected semantic mutation. P8 CUDA may extend the
same equivalence matrix later, but no CUDA device or artifact is required to
retire this P4 task. Byte identity holds only under a frozen algorithm policy.

## Invariants

- Identical declared source/profile/compiler/algorithm/seed/backend policy
  yields reproducible artifact bytes or a stated canonical normalization.
- Different valid CPU/CUDA/optimizer choices may yield different artifacts,
  each with its own hash and independently checked source-IR equivalence;
  cross-backend byte identity is required only when explicitly guaranteed.
- The end-to-end fixture demonstrates the intended behavior from admitted
  source/input through the actual generated/executed Malbolge path.

## Evidence Boundary

- Expected durable artifact surface: `docs/technical/examples/`,
  `tests/applications/`, `benchmarks/applications/`, `runtime/`.
- Required evidence: reproducible build/run commands, expected outputs or
  interaction traces, artifact hashes, and end-to-end verification.
- Prerequisite completion evidence: `malbolge-layout-and-encoding-backend`,
  `differential-vm-verification`.

## Diagnostics

Missing external inputs or unmet target capabilities fail explicitly;
demonstrations may not substitute host logic for guest behavior.

## Examples

- No normative example is required at this planning stage unless the contract
  states one.

## Implementation

Not implemented. This proposed contract does not claim executable support yet.

## References

- [Compiler Pipeline And Guest
  Runtime](../adr/compiler-pipeline-and-guest-runtime.md)
- [Verification Trust Boundary](../adr/verification-trust-boundary.md)

### Governing ADR Paths

- `docs/technical/adr/compiler-pipeline-and-guest-runtime.md`
- `docs/technical/adr/verification-trust-boundary.md`
