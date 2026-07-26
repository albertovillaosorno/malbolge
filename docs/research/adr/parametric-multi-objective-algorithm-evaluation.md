# Parametric Multi-Objective Algorithm Evaluation

## Status

Accepted.

## Context

Fixed demonstrations such as a game can saturate: two algorithms may both exceed
a usability threshold while differing greatly in scaling, resource use, or code
quality. Compiler research needs workloads whose difficulty can continue to grow
and measurements that preserve tradeoffs.

## Decision

Research algorithms are evaluated primarily through deterministic parametric
challenge families and multi-objective evidence.

A challenge identifies family, version, seed, target profile, explicit
difficulty parameters, and a semantic oracle. Comparisons record maximum-solved
difficulty under fixed budgets plus time-to-verified-solution, generated-code
size, runtime work, RAM/VRAM, verifier cost, stochastic success probability, and
other justified resource metrics.

Capacity curves and Pareto frontiers are authoritative comparison artifacts. A
single convenience score may be derived for dashboards but cannot replace the
underlying multidimensional evidence.

The challenge schema is machine-readable so human researchers and LLM-based
agents can propose algorithms against the same verifier. An agent never
self-certifies correctness.

## Alternatives Considered

### One flagship application benchmark

Rejected as the primary scientific metric because performance differences vanish
once all algorithms cross the application's fixed usability threshold.

### One aggregate score

Rejected as authoritative because weighting hides whether an algorithm trades
memory, runtime, compilation cost, success probability, or output size.

## Consequences

- DOOM remains a valuable real-world interoperability demonstration but not the
  scientific definition of optimizer quality.
- Research reports must retain raw multidimensional evidence.
- Challenge generators and semantic oracles become reusable research
  infrastructure.

## Implementation Notes

Difficulty need not be mathematically monotonic for every individual instance,
but families must expose enough controlled scaling to support capacity studies
and reproducible comparisons.
