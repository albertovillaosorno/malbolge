# LaTeX mathematical specification framework

## Status

Active implementation

## Purpose

Create a `math/` surface of `.tex` specifications for ternary words,
rotation, crazy operation, decoding, self-modification, memory models, compiler
lowering, equivalence relations, and search cost functions.

## Scope

This document governs `docs/technical/specification/mathematics/` behavior
described below.

## Current Behavior

### Shared notation and profile model

`src/specification/formal-model/math/malbolge-notation.tex` is the common
notation include for standalone
mathematical documents. It fixes repository-wide symbols for ternary word
families, rotate/crazy operations, decode/encryption, observable equivalence,
compiler lowering, verification, and cost vectors. Standalone documents may add
local notation but must not silently redefine those shared semantic symbols.

`src/specification/formal-model/math/specification/profile-model.tex` defines
the profile-width model for a
positive trit count `N`: word modulus `3^N`, modular memory/register domains,
profile-width rotate/crazy operations, decode/self-encryption order, byte I/O,
EOF as the all-two-trit word, loading notation, execution transitions, and
observable equivalence. It explicitly specializes the model to historical
10-trit and current 14-trit profiles without mutating the written 1998 contract.

`src/specification/formal-model/math/specification/malbolge-1998.tex` remains
the normative classic arithmetic
specialization and imports the same notation surface.

### Build and validation boundary

`src/automation/repository/composition/scripts/validate/math_specifications.py`
discovers every standalone `.tex`
document under `math/`, requires the shared notation include, and compiles each
document independently with `pdflatex`. Builds disable package auto-installation
and TeX shell escape and write only beneath `.cache/latex/`.

The current repository has nine standalone mathematical documents. All nine
compile through the validator. `tests/mathematics/test_math_framework.py` locks
the document set, shared-notation requirement, cache-only output mapping, and
the
historical/current profile-width specializations.

The framework makes equations stable and buildable; it does not by itself prove
that executable implementations satisfy them.
Exhaustive/property/machine-checked
correspondence remains a separate downstream obligation.

## Invariants

- Normative equations have stable notation/definitions and a buildable LaTeX
  structure that can be referenced by research records and executable
  correspondence tests.
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
  `historical-malbolge-semantics-specification`.
- Build evidence:
<!-- jig-ignore-next-line: canonical path or identifier is indivisible -->
  `src/automation/repository/composition/scripts/validate/math_specifications.py`
  compiles all nine
  standalone documents with package installation and shell escape disabled.
- Layout evidence: `tests/mathematics/test_math_framework.py` verifies shared
  notation, cache-only artifacts, and canonical profile-width specializations.
- Executable or machine-checked semantic correspondence remains owned by the
  separate `machine-checked-mathematical-correspondence` work rather than being
  inferred from a successful LaTeX build.
## References

- [Verification Trust Boundary](../../adr/verification-trust-boundary.md)
- [Research Evidence And Algorithm
  Mirror](../../../research/adr/research-evidence-and-algorithm-mirror.md)
