# Human-scale Malbolge search study

- Status: Proposed
- Record type: Study
- Planning identity: `human-scale-malbolge-search-study`
- Last reviewed: 2026-07-26

## Governing Decisions

- [Research Evidence And Algorithm
  Mirror](../adr/research-evidence-and-algorithm-mirror.md)
- [Parametric Multi Objective Algorithm
  Evaluation](../adr/parametric-multi-objective-algorithm-evaluation.md)

## Purpose

Create a bounded experiment illustrating why manual Malbolge synthesis is
cognitively impractical even for very capable humans, separating attention and
energy limits from machine-search throughput without bogus IQ or neuroscience
claims.

## Evidence Model

- The study uses bounded reproducible tasks and measured search-space/work
  estimates and avoids unsupported IQ, cognition, or neuroscience claims about
  human capability.
- The research record separates observed evidence from interpretation and
  preserves negative/null outcomes that affect the conclusion.
- The work states a falsifiable question or hypothesis, an explicit baseline,
  and an observation that would reject or materially weaken the proposed
  technique before performance conclusions are accepted.
- If executable algorithm research is required, the stable ID is mirrored under
  `docs/research/algorithms/<id>/` and `algorithms/<id>/`; ordinary product
  engineering is not forced into that mirror.
- Performance conclusions use equivalent workloads and report raw-sample
  provenance, resource budgets, dispersion/uncertainty, and failure/success
  behavior rather than only a best-case number.

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
- Performance evidence pending: raw measurements plus a reproducible
  scaling/statistical summary tied to exact workload and hardware/software
  identity.

## Current Status

No completed research result or implementation claim is made by this proposed
record.
