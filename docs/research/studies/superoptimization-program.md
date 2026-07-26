# Superoptimization research program

- Status: Proposed
- Record type: Study
- Planning identity: `superoptimization-research-program`
- Last reviewed: 2026-07-26

## Governing Decisions

- [Research Evidence And Algorithm
  Mirror](../adr/research-evidence-and-algorithm-mirror.md)

## Purpose

Ask which search strategies find smaller or faster verified Malbolge blocks
under fixed time and evaluation budgets. Build a rigorous research track
covering stochastic superoptimization, enumerative synthesis, equality
saturation where applicable, Monte Carlo and evolutionary search, program-state
canonicalization, pruning, translation validation, learned guidance, GPU batch
evaluation, and prior Malbolge code generation techniques. Maintain a source-
backed bibliography and convert useful results into explicit compiler
hypotheses, benchmarks, and mathematical `.tex` work rather than folklore.

## Evidence Model

- The program maintains a source-backed map from prior
  superoptimization/synthesis work to falsifiable Malbolge-specific hypotheses
  and records both adopted and rejected techniques.
- The research record separates observed evidence from interpretation and
  preserves negative/null outcomes that affect the conclusion.
- The work states a falsifiable question or hypothesis, an explicit baseline,
  and an observation that would reject or materially weaken the proposed
  technique before performance conclusions are accepted.
- If executable algorithm research is required, the stable ID is mirrored under
  `docs/research/algorithms/<id>/` and `algorithms/<id>/`; ordinary product
  engineering is not forced into that mirror.

## Method Or Procedure

Work under this record uses stable identities, explicit inputs and assumptions,
independent correctness evidence where applicable, and retained negative/null
results. Source claims resolve through `docs/bibliography/`.

## Verification And Review

- Expected durable artifact surface: `docs/research/`, `algorithms/`,
  `benchmarks/research/`.
- Required evidence: research question, hypotheses/baselines, source trail,
  experiment manifest, raw-output provenance, results, and threats to validity.
- Research evidence pending: bibliography-backed context, experiment identity,
  reproducible configuration, retained negative/null results, and a reviewed
  conclusion with threats to validity.

## Current Status

No completed research result or implementation claim is made by this proposed
record.
