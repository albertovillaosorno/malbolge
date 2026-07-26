# Deterministic logical concurrency

- Status: Proposed
- Planning identity: `deterministic-logical-concurrency`
- Last reviewed: 2026-07-26

## Governing Decisions

- [Tiered Native Execution](../adr/tiered-native-execution.md)
- [Verification Trust Boundary](../adr/verification-trust-boundary.md)

## Purpose

Define deterministic logical tasks and joins that serialize under Malbolge while
allowing proven-independent host work to execute concurrently with identical
observable results.

## Proposed Model

This record defines the contract that implementation must satisfy for
`deterministic-logical-concurrency`. The implementation may change internal
representation or language choices without changing the observable behavior,
trust boundary, or ownership rules stated by its governing decisions.

## Invariants

- Host parallelism is admitted only for work proven observationally independent;
  changing worker count or scheduling cannot change guest-visible I/O, state, or
  generated artifacts.
- Observable state, I/O, termination, and diagnostics match the declared
  semantic profile across positive, boundary, and adversarial fixtures.
- The work states a falsifiable question or hypothesis, an explicit baseline,
  and an observation that would reject or materially weaken the proposed
  technique before performance conclusions are accepted.
- If executable algorithm research is required, the stable ID is mirrored under
  `docs/research/algorithms/<id>/` and `algorithms/<id>/`; ordinary product
  engineering is not forced into that mirror.

## Failure Behavior

Invalid programs, unsupported profiles, or broken native assumptions fail
deterministically without changing guest-visible state silently.

## Verification

- Expected durable artifact surface: `vm/`, `execution/`, `tests/vm/`,
  `benchmarks/interpreter/`.
- Required evidence: semantic fixtures, state/I/O traces where diagnostic, and
  differential results against independent specification-conformant
  implementations; the historical interpreter is compared only on its documented
  agreement domain.
- Research evidence pending: bibliography-backed context, experiment identity,
  reproducible configuration, retained negative/null results, and a reviewed
  conclusion with threats to validity.

## Implementation Status

Not implemented. This proposed contract does not claim executable support yet.
