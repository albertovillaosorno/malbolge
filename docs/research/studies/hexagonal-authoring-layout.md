# Hexagonal authoring-layout experiment

## Status

Proposed

## Research Question

What evidence and method are required to evaluate hexagonal authoring-layout
experiment?

## Background

Research an optional graph or hexagonal authoring representation that lowers to
ordinary linear `.malbolge` output and therefore does not require a special
execution engine for compatible programs.

- Status: Proposed
- Record type: Study
- Planning identity: `hexagonal-authoring-layout-experiment`
- Last reviewed: 2026-07-26

## Prior Work

Prior-work claims must resolve through canonical records under
`docs/bibliography/`.

## Hypothesis

- The experiment measures whether alternate authoring/module layouts improve
  compiler/research ergonomics without creating language-based repository
  boundaries or changing emitted semantics.
- Classic programs inside the original defined domain remain observationally
  identical while current profile-dependent behavior is gated by explicit target identity.
- The work states a falsifiable question or hypothesis, an explicit baseline,
  and an observation that would reject or materially weaken the proposed
  technique before performance conclusions are accepted.
- If executable algorithm research is required, the stable ID is mirrored under
  `docs/research/algorithms/<id>/` and `algorithms/<id>/`; ordinary product
  engineering is not forced into that mirror.

## Method

Work under this record uses stable identities, explicit inputs and assumptions,
independent correctness evidence where applicable, and retained negative/null
results. Source claims resolve through `docs/bibliography/`.

## Evidence

- Expected durable artifact surface: `compatibility/`,
  `docs/technical/specification/`, `tests/compatibility/`.
- Required evidence: classic compatibility corpus plus extension/profile
  boundary fixtures and exact diagnostics.
- Research evidence pending: bibliography-backed context, experiment identity,
  reproducible configuration, retained negative/null results, and a reviewed
  conclusion with threats to validity.

## Results

No completed research result or implementation claim is made by this proposed
record.

## Threats to Validity

The record is proposed; implementation bias, workload selection, hardware
effects, and incomplete replication remain threats until measured.

## Conclusion

Open. No technique is promoted to product architecture until the declared
evidence supports it.

## References

- `docs/technical/adr/specification-authority-and-malbolge-evolution.md`
- [Research Evidence And Algorithm
  Mirror](../adr/research-evidence-and-algorithm-mirror.md)
