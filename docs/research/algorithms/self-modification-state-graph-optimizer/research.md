# Self-modification state-graph optimizer

## Status

Active

## Research Question

Does `self-modification-state-graph-optimizer` provide a reproducible verified
benefit over its declared baseline for the Malbolge compiler or execution
problem without weakening semantic correctness?

## Background

Model executable Malbolge regions as versioned state-transition graphs whose
nodes capture only semantically relevant code/data state. Derive mathematically
verified reductions that collapse equivalent mutation histories, eliminate
redundant encryption/update work, hoist invariant crazy/rotate computations, and
identify regions safe for direct native execution. Express the equivalence and
reduction rules in `.tex` and validate each admitted rewrite against executable
VM evidence.

- Status: Active
- Research ID: `self-modification-state-graph-optimizer`
- Last reviewed: 2026-07-26

## Prior Work

- `../../../bibliography/publications/superoptimization/egg.md`

## Hypothesis

- Baseline hypothesis: exact-state deduplication can reuse identical classic VM
  observations without changing graph edges or execution semantics even when the
  digest function collides adversarially.
- Reduction hypothesis (future): a smaller future-relevant key can merge more
  states than the exact baseline while preserving every admitted future
  observation on its declared domain.
- H0/rejection condition: any hash-only merge, any unequal exact snapshots merged
  by the baseline, or any reduced-key pair whose future observations diverge
  rejects the corresponding technique immediately.

## Method

The executable mirror lives at
`algorithms/self-modification-state-graph-optimizer/`. Experiments use versioned
configuration, explicit seeds where stochastic behavior exists, fixed resource
budgets, parametric challenge identities, and the same verifier used for
baselines. Raw regenerable output stays in the mirror's Git-ignored `out/`.

## Evidence

Candidate generation, heuristics, models, and accelerators are untrusted. A
research result can compare quality or cost only after the trusted semantic
verifier accepts the candidate under the declared target profile.

- The research identifies the minimal future-relevant state and observational
  equivalence relation, then proves/test-validates every graph merge or
  mutation-history collapse before using it for native execution.
- Definitions state domains and assumptions precisely; executable code cannot
  claim a mathematical reduction outside those stated preconditions.
- The work states a falsifiable question or hypothesis, an explicit baseline,
  and an observation that would reject or materially weaken the proposed
  technique before performance conclusions are accepted.
- If executable algorithm research is required, the stable ID is mirrored under
  `docs/research/algorithms/<id>/` and `algorithms/<id>/`; ordinary product
  engineering is not forced into that mirror.
- Every correctness-relevant equation or equivalence used by implementation has
  explicit domain assumptions and a traceable executable correspondence check.

## Results

The exact-state baseline is executable in
`algorithms/self-modification-state-graph-optimizer/state_graph.rs`. A node is
confirmed by complete classic profile identity, registers, deterministic input
and cursor, committed output prefix, termination state, and all 59,049 memory
words. FNV-1a is used only to select a comparison bucket.

Three deterministic fixtures currently pass:

- replaying the same bounded execution reuses nodes and edges;
- forcing every snapshot to digest `0` still keeps distinct input states in
  separate nodes because complete snapshots are compared;
- only normative specification mode is admitted by this baseline.

`math/algorithms/self-modification-state-graph-optimizer.tex` formalizes the
exact projection and collision-safe merge rule. Both equations are registered in
`math/specification/correspondence.toml` and mapped directly to the algorithm's
owned tests.

The first reduced-state key is now admitted for one structural fact:
`future_input_snapshot` removes only the contents of bytes strictly before the
committed input cursor while retaining that cursor and the exact remaining input
suffix. The `cbO` fixture (`<`, `<`, `v`) exhausts all 256 possible first input
bytes, applies one common second byte that overwrites `A`, and proves the reduced
keys are equal both before and after the common future halt.

A second structural reduction is also admitted for already terminated states.
`terminal_future_snapshot` keeps profile identity, committed output prefix, and
termination reason while dropping memory, registers, and input state. Fixtures
vary valid halt-source memory, `A/D`, and input and still produce one future key;
a live machine is rejected from this domain.

The exact baseline now also consumes the runtime-owned
`ProfileMachineState` checkpoint directly. `profile.rs` indexes the complete
validated checkpoint by profile fingerprint, I/O state, registers, and every
profile memory word; a current `malbolge-2026.2` replay deduplicates and a forced
constant digest does not merge checkpoints with different input. This extends the
correctness oracle to 4,782,969-word current states without duplicating checkpoint
validation.

These results do not justify removing the live input cursor, changing the
remaining suffix, removing live output history, reducing live memory/registers,
or claiming a performance improvement. Full current checkpoints are explicitly a
correctness/deoptimization baseline; their copy/hash/storage cost must be measured
before any production graph architecture adopts them.

## Threats to Validity

Initial threats include challenge-family bias, hardware/toolchain sensitivity,
search-seed variance, verifier bounds, and overfitting to small Malbolge blocks.
Each experiment must narrow these threats before drawing a conclusion.

## Conclusion

Accept exact-state deduplication as the conservative graph baseline and admit
the exact baseline for both classic and validated current-profile checkpoints,
plus two structural reductions: consumed input-prefix contents are
future-irrelevant when cursor/suffix stay exact, and already-terminated states
may drop dead memory/register/input state while retaining
profile/output/termination. Do not yet promote live memory/register/output
reductions or a native-execution shortcut. Each further reduction must
independently defeat the exact baseline.

## References

- [Verification Trust
  Boundary](../../../technical/adr/verification-trust-boundary.md)
- [Research Evidence And Algorithm
  Mirror](../../adr/research-evidence-and-algorithm-mirror.md)
