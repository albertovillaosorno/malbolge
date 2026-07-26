# Compiler algorithm experimentation platform

- Status: Proposed
- Record type: Methodology
- Planning identity: `compiler-algorithm-experimentation-platform`
- Last reviewed: 2026-07-26

## Governing Decisions

- [Repository Responsibility
  Boundaries](../../technical/adr/repository-responsibility-boundaries.md)
- [Research Evidence And Algorithm
  Mirror](../adr/research-evidence-and-algorithm-mirror.md)
- [Parametric Multi Objective Algorithm
  Evaluation](../adr/parametric-multi-objective-algorithm-evaluation.md)

## Purpose

Make the repository a reproducible laboratory for compiler research, not merely
an implementation of one fixed C-to-Malbolge pipeline. Experimental algorithms
use the `docs/research/algorithms/<id>/` and `algorithms/<id>/` mirror, while
ordinary product algorithms remain inside their owning responsibility. Provide
stable experiment boundaries for alternate IRs, lowering passes, graph
simplifiers, superoptimizers, search strategies, code generators, execution
tiers, and cost models. Experiments must be selectable without editing trusted
semantic code, record exact configuration/seeds/inputs, compare against common
correctness oracles, and emit reproducible evidence so a new algorithm can be
accepted, rejected, or retired without becoming architecture by accident.

## Evidence Model

- A new experimental compiler algorithm can be added, configured, compared
  against a baseline, verified, and removed without editing trusted VM/compiler
  semantics.
- The authoritative rule/specification is deterministic, versionable, and does
  not depend on undocumented host behavior.
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

- Expected durable artifact surface: `algorithms/`, `docs/research/`,
  `benchmarks/`, `tests/`.
- Required evidence: reviewed authority text plus deterministic
  parser/schema/governance tests for the declared boundary.
- Research evidence pending: bibliography-backed context, experiment identity,
  reproducible configuration, retained negative/null results, and a reviewed
  conclusion with threats to validity.

## Current Status

No completed research result or implementation claim is made by this proposed
record.
