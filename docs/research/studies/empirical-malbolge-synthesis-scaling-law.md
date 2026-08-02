# Empirical Malbolge synthesis scaling law

## Status

Proposed

## Research Question

How does verified Malbolge synthesis cost actually scale as problem difficulty,
self-modification coupling, layout sensitivity, and reusable verified knowledge
grow?

## Background

Blind sequence search has a combinatorial candidate space, but the practical
compiler is not limited to blind search. It can decompose programs, reuse
verified blocks, canonicalize state, prune dominated candidates, apply learned
guidance, and evaluate candidates on accelerators. The project therefore must
measure scaling rather than casually label compilation exponential, linear, or
constant-time.

- Status: Proposed
- Record type: Study
- Planning identity: `empirical-malbolge-synthesis-scaling-law`
- Last reviewed: 2026-07-26

## Prior Work

Prior-work claims resolve through canonical records under
`docs/bibliography/`. The superoptimization, synthesis, search, and verification
records define the starting evidence base.

## Hypothesis

- Raw unconstrained search cost grows much faster than compositional compilation
  on challenge families with equivalent semantics.
- Verified catalogue coverage reduces marginal search cost for recurring
  semantic
  blocks, but layout and self-modification coupling can reintroduce non-local
  costs.
- No single asymptotic model is assumed to fit all difficulty ranges, target
  profiles, or search strategies.
- Learned or stochastic guidance may improve time-to-first-verified candidate
  but
  does not change correctness authority.

## Method

Use the parametric challenge generator to vary one or more difficulty dimensions
while preserving stable semantic oracles. For each family and fixed resource
budget, compare blind/enumerative search, structured deterministic search,
canonicalization/pruning, verified block reuse, stochastic/guided search, and
available accelerator-backed evaluators.

Record at least candidate evaluations, wall time, verifier time, memory/VRAM,
search success rate, generated-code size, catalogue hit rate, invalidation or
relink work, and marginal cost of increasing difficulty. Fit competing models
only after collecting evidence and report residuals/change points instead of
choosing a preferred complexity class in advance.

## Evidence

- Raw samples retain exact challenge identity, seed, target profile, algorithm,
  hardware/software identity, resource budget, catalogue version, and verifier
  identity.
- Capacity curves distinguish solved difficulty from merely faster easy cases.
- Cold search, warm catalogue reuse, verification, linking, and cache effects
  are
  reported separately.
- Null results and failed model fits remain versioned evidence.

## Results

No scaling law has been established. Any statement that practical compilation is
linear, exponential, sublinear, or constant-time remains a hypothesis until this
study produces reproducible evidence.

## Threats to Validity

Challenge-family construction, hidden correlations between difficulty axes,
finite hardware budgets, catalogue warm-up, stochastic variance, verifier cost,
and implementation maturity can all distort apparent scaling. Results from one
family or device must not be generalized to whole-program compilation without
additional evidence.

## Conclusion

Open. The study exists specifically to prevent attractive but unsupported
complexity claims from becoming architecture folklore.

## References

- [Research Evidence And Algorithm
  Mirror](../adr/research-evidence-and-algorithm-mirror.md)
- [Parametric Multi Objective Algorithm
  Evaluation](../adr/parametric-multi-objective-algorithm-evaluation.md)
- [Superoptimization program](superoptimization-program.md)
- [Parametric challenges](../methodology/parametric-challenges.md)
