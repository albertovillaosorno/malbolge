# Hexagonal authoring-layout experiment

- Status: Proposed
- Record type: Study
- Planning identity: `hexagonal-authoring-layout-experiment`
- Last reviewed: 2026-07-26

## Governing Decisions

- [Historical Compatibility And Malbolge
  Evolution](../../technical/adr/specification-authority-and-malbolge-evolution.md)
- [Research Evidence And Algorithm
  Mirror](../adr/research-evidence-and-algorithm-mirror.md)

## Purpose

Research an optional graph or hexagonal authoring representation that lowers to
ordinary linear `.malbolge` output and therefore does not require a special
execution engine for compatible programs.

## Evidence Model

- The experiment measures whether alternate authoring/module layouts improve
  compiler/research ergonomics without creating language-based repository
  boundaries or changing emitted semantics.
- Classic programs inside the original defined domain remain observationally
  identical while extension-only behavior is gated by explicit profile identity.
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

- Expected durable artifact surface: `compatibility/`,
  `docs/technical/specification/`, `tests/compatibility/`.
- Required evidence: classic compatibility corpus plus extension/profile
  boundary fixtures and exact diagnostics.
- Research evidence pending: bibliography-backed context, experiment identity,
  reproducible configuration, retained negative/null results, and a reviewed
  conclusion with threats to validity.

## Current Status

No completed research result or implementation claim is made by this proposed
record.
