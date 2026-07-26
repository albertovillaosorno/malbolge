# Compact guest bytecode strategy

- Status: Proposed
- Research ID: `compact-guest-bytecode-strategy`
- Last reviewed: 2026-07-26

## Governing Decisions

- [Compiler Pipeline And Guest
  Runtime](../../../technical/adr/compiler-pipeline-and-guest-runtime.md)
- [Deterministic C Surface And Clang
  Tooling](../../../technical/adr/deterministic-c-surface-and-clang-tooling.md)
- [Verification Trust
  Boundary](../../../technical/adr/verification-trust-boundary.md)

## Question

Does `compact-guest-bytecode-strategy` provide a reproducible verified benefit
over its declared baseline for the Malbolge compiler or execution problem
without weakening semantic correctness?

## Hypotheses

- H1: the proposed technique improves at least one preregistered objective under
  an equivalent resource budget while all accepted outputs pass the independent
  verifier.
- H0/rejection condition: the technique is unsound, cannot reproduce its result,
  or provides no meaningful advantage over the declared baseline on the admitted
  challenge distribution.

## Research Objective

Evaluate a VM-inside-Malbolge strategy where large programs are represented as
compact bytecode interpreted by a reusable Malbolge runtime when that reduces
code-size explosion or compilation cost.

## Prior Work

- [Llvm Ir](../../../bibliography/compiler-and-runtime/llvm-ir.md)

## Method

The executable mirror lives at `algorithms/compact-guest-bytecode-strategy/`.
Experiments use versioned configuration, explicit seeds where stochastic
behavior exists, fixed resource budgets, parametric challenge identities, and
the same verifier used for baselines. Raw regenerable output stays in the
mirror's Git-ignored `out/`.

## Correctness Boundary

Candidate generation, heuristics, models, and accelerators are untrusted. A
research result can compare quality or cost only after the trusted semantic
verifier accepts the candidate under the declared target profile.

## Measurements

- The research compares direct lowering with a reusable guest bytecode/runtime
  design on code size, compile time, runtime cost, memory pressure, and verifier
  complexity before adoption.
- The stage has deterministic input/output form, rejects malformed or
  unsupported input explicitly, and preserves source/profile provenance needed
  downstream.
- The work states a falsifiable question or hypothesis, an explicit baseline,
  and an observation that would reject or materially weaken the proposed
  technique before performance conclusions are accepted.
- If executable algorithm research is required, the stable ID is mirrored under
  `docs/research/algorithms/<id>/` and `algorithms/<id>/`; ordinary product
  engineering is not forced into that mirror.

## Results

No experiment result is recorded yet.

## Threats To Validity

Initial threats include challenge-family bias, hardware/toolchain sensitivity,
search-seed variance, verifier bounds, and overfitting to small Malbolge blocks.
Each experiment must narrow these threats before drawing a conclusion.

## Conclusion

No conclusion is accepted before reproducible evidence exists.
