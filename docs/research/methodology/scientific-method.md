# Academic research methodology and evidence model

- Status: Proposed
- Record type: Methodology
- Planning identity: `academic-research-methodology-and-evidence-model`
- Last reviewed: 2026-07-26

## Governing Decisions

- [Research Evidence And Algorithm
  Mirror](../adr/research-evidence-and-algorithm-mirror.md)

## Purpose

Define the repository-wide scientific method for compiler research: falsifiable
questions, preregistered hypotheses where practical, correctness/performance
separation, negative and null result retention, threats to validity,
replication, source quality, experiment provenance, and criteria for claiming
that evidence supports or rejects a technique.

## Evidence Model

- The methodology distinguishes research question, hypothesis, baseline,
  falsification condition, correctness evidence, performance evidence,
  negative/null result, replication, and threat to validity.
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
