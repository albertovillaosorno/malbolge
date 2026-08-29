# Machine-checked mathematical correspondence

## Status

Accepted implementation

## Purpose

Connect mathematical specifications to executable tests or proof tooling so the
`.tex` files are reviewable mathematics rather than decorative documentation.

## Scope

This document governs `docs/technical/specification/mathematics/` behavior
described below.

## Current Behavior

### Equation identity and manifest

Correctness-relevant equations promoted into executable correspondence use a
stable `eq:*` LaTeX label.
`src/specification/formal-model/math/specification/correspondence.toml` is the
closed versioned
manifest that maps each promoted equation to its exact mathematical source,
claimed domain/coverage class, and one or more executable test functions.

`src/automation/repository/composition/scripts/validate/math_correspondence.py`
validates the graph fail-closed. It
requires unique manifest IDs/labels, repository-relative sources that reject
absolute, Windows drive/root, and parent-traversal forms on every validator
host,
evidence under
repository `tests/` or an algorithm mirror's `algorithms/<id>/tests/`, exact
existence of every referenced `fn`/`def`, and exact set
equality between all `eq:*` labels under
`src/specification/formal-model/math/specification/` and the manifest.
Renaming/removing an equation or a test therefore breaks correspondence instead
of silently leaving stale documentation.

### Current promoted equations

The accepted graph contains 40 promoted equations: 19 from the
self-modification state-graph model, 14 from the generic profile model, four
from Malbolge-specific optimization mathematics, and three from the classic
1998 specialization.

The manifest deliberately reuses independent evidence rather than duplicating
semantics in a new proof harness. Coverage currently includes:

- exhaustive classic word-domain and successor equations, all 94 graphical
  post-encryption inputs, full classic loader recurrence, rotate/positional
  decode, and crazy-table chunk decomposition;
- all 94 loader decode phases, invalid source byte classes, recurrence-base and
  capacity edges;
- 24 seed/ordinal-replayable classic-versus-profiled programs with step-by-step
  comparison and all 59,049 final memory cells;
- current N15 scalar rotate/crazy/loading fixtures, current EOF tracing, and
  atomic post-jump encryption rejection.

A manifest link does not upgrade fixture coverage into a proof outside its
stated `domain` and `mechanism`. New compiler or research equations become
eligible only when their owning implementation exists; that owning work must
extend this closed graph before making a correctness claim.

## Invariants

- Executable arithmetic/state transitions are checked against the formal
  definitions over exhaustive bounded domains or another explicit
  machine-checked correspondence mechanism.
- Definitions state domains and assumptions precisely; executable code cannot
  claim a mathematical reduction outside those stated preconditions.
- Every correctness-relevant equation or equivalence used by implementation has
  explicit domain assumptions and a traceable executable correspondence check.

## Failure Behavior

A rule outside its stated domain is inapplicable; the implementation may not
extrapolate a proof by convention.

## Verification

- Expected durable artifact surface: `math/`, `docs/research/algorithms/`,
  `algorithms/`, `tests/mathematics/`.
- Required evidence: `.tex` definitions/derivations plus exhaustive,
  property-based, or machine-checked correspondence for the admitted domain.
- Prerequisite completion evidence:
  `latex-mathematical-specification-framework`, `safe-rust-malbolge-vm`,
  `property-fuzz-and-exhaustive-testing`.
<!-- jig-ignore-next-line: canonical path or identifier is indivisible -->
- `src/automation/repository/composition/scripts/validate/math_correspondence.py`
  closes 40 promoted equation labels against concrete test functions.
- `tests/mathematics/test_correspondence_manifest.py` proves orphan labels,
  stale test functions, and duplicate TOML authority fail closed.
- Semantic evidence is executed by the mapped Rust/Python suites; the manifest
  is traceability, not a substitute oracle.
- Future implementation-relevant equations must extend the manifest and its
  independent evidence from the owning compiler, optimizer, or research TODO.
## References

- [Verification Trust Boundary](../../adr/verification-trust-boundary.md)
- [Research Evidence And Algorithm
  Mirror](../../../research/adr/research-evidence-and-algorithm-mirror.md)
