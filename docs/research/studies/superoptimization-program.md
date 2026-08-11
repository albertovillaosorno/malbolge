# Superoptimization research program

## Status

Active

## Research Question

Which search strategies find smaller or faster independently verified Malbolge
blocks under equal time and candidate-evaluation budgets?

## Background

Ask which search strategies find smaller or faster verified Malbolge blocks
under fixed time and evaluation budgets. Build a rigorous research track
covering stochastic superoptimization, enumerative synthesis, equality
saturation where applicable, Monte Carlo and evolutionary search, program-state
canonicalization, pruning, translation validation, learned guidance, GPU batch
evaluation, and prior Malbolge code generation techniques. Maintain a source-
backed bibliography and convert useful results into explicit compiler
hypotheses, benchmarks, and mathematical `.tex` work rather than folklore.

- Status: Active
- Record type: Study
- Planning identity: `superoptimization-research-program`
- Last reviewed: 2026-08-09

## Prior Work

The initial source map uses three canonical primary-source records. STOKE
provides the stochastic-search comparison point, Souper provides the
synthesis-over-IR comparison point, and `egg` provides the equality-saturation
comparison point. None is assumed to transfer directly to self-modifying
Malbolge.

- `../../bibliography/publications/superoptimization/stoke.md`
- `../../bibliography/publications/superoptimization/souper.md`
- `../../bibliography/publications/superoptimization/egg.md`

### Technique-to-hypothesis map

**STOKE-style stochastic search.** Hypothesis: proposal search lowers time to
first verified block at an equal evaluation budget. The baseline is stable
deterministic enumeration over the same candidate language. Reject or materially
weaken the hypothesis when no preregistered challenge family improves, or when
verifier acceptance differs between otherwise equivalent comparisons.

**Souper-style synthesis over IR.** Hypothesis: a smaller semantic IR reduces
candidate work before Malbolge layout compared with raw-byte synthesis. The
baseline is synthesis over the equivalent raw Malbolge candidate surface. Reject
or materially weaken the hypothesis when solver plus validation work is not
reduced, or when lowering loses exact equivalence.

**`egg`-style equality saturation.** Hypothesis: e-graphs reduce rewrite-order
sensitivity for pure pre-layout expressions whose equivalences are independently
checkable. The baseline is deterministic ordered rewriting over the same
admitted equivalences. Reject or materially weaken the hypothesis when
self-modifying state must enter the e-graph relation, proof obligations cannot
be
discharged, or resource use dominates the baseline.

The already implemented exact-byte duplicate pruning is a conservative
correctness baseline, not evidence that any of the three broader techniques is
faster. Future comparisons use the same parametric challenge identities, target
profile, verifier, wall-clock/evaluation budgets, and retained failure counts.

## Hypothesis

- The program maintains a source-backed map from prior
  superoptimization/synthesis work to falsifiable Malbolge-specific hypotheses
  and records both adopted and rejected techniques.
- Raw combinatorial search, decomposition, verified block reuse,
  canonicalization,
  pruning, heuristic search, and learned guidance are compared rather than
  collapsed into one claim about compiler complexity.
- The research record separates observed evidence from interpretation and
  preserves negative/null outcomes that affect the conclusion.
- The work states a falsifiable question or hypothesis, an explicit baseline,
  and an observation that would reject or materially weaken the proposed
  technique before performance conclusions are accepted.
- If executable algorithm research is required, the stable ID is mirrored under
  `docs/research/algorithms/<id>/` and `algorithms/<id>/`; ordinary product
  engineering is not forced into that mirror.

## Method

Every comparison fixes the challenge family/version/seed/profile, semantic
verifier, candidate language, and either wall-clock or candidate-evaluation
budget before comparing strategies. A strategy reports time to first verified
candidate, accepted-candidate quality, total verifier work, and failure/null
outcomes; verifier rejection never becomes search success. Where randomness is
used, the seed set and aggregate distribution are part of the experiment
identity rather than selecting only the best run.

The deterministic enumeration and exact-byte duplicate-pruning paths are the
initial correctness baselines. The first preregistered comparison is mirrored as
`superoptimization-research-program`: a classic-profile stochastic-proposal
pilot against deterministic enumeration with fixed seed, target fingerprint,
wall-clock, candidate-evaluation, memory, and verifier bounds. Candidate-order
mechanics are now executable: natural enumeration is the baseline order and a
version-stable SplitMix64 sparse partial Fisher-Yates schedule defines the
seeded no-replacement proposal order. The pilot candidate language is now frozen
before measurement as every two-graphical-byte classic source (8,836 members),
with independent acceptance only for one- or two-transition halts that perform
no
prior input/output and quality equal to transitions-to-halt. Exhaustive verifier
characterization finds ten accepted members. A preregistered five-repetition
seed-zero pilot is now retained: seeded ordering reaches the first verified
candidate in 250 evaluations versus 706 for enumeration, with best quality 1 on
both paths. First-hit median elapsed time also favors seeded order on the
recorded host, while full-corpus medians overlap and are effectively tied. This
supports only the frozen pilot's first-hit objective; it is not a general
stochastic-search or throughput result. New synthesis,
equality-saturation, learned, or accelerator-guided strategies must add their
own equally identified comparisons rather than inheriting a result from that
pilot. Source claims resolve through `docs/bibliography/`.

## Evidence

- Expected durable artifact surface: `docs/research/`, `algorithms/`,
  `benchmarks/research/`.
- Required evidence: research question, hypotheses/baselines, source trail,
  experiment manifest, raw-output provenance, results, and threats to validity.
- Initial bibliography-backed technique mapping and falsifiable rejection
  conditions are recorded above. The first schema-one experiment plan,
  lifecycle record, two-sided research mirror, concrete workload/verifier
  identity, exhaustive corpus characterization, and replay-locked
  candidate-order substrate established reproducible identity before
  measurement. The first tracked run now retains all five raw repetitions plus
  generated run/benchmark identity and exact regression tests. Additional seeds,
  larger challenges, retained negative/null results, additional technique plans,
  independent-host replication, and a stronger comparative conclusion remain
  pending.

## Results

The first seed-zero classic pilot supports the first-hit objective only: 250
seeded evaluations to first verification versus 706 for deterministic
enumeration, with equal best quality. Host timing likewise favors seeded
first-hit median, but full-corpus runtime does not separate materially. No
product implementation or general technique-superiority claim is made.

## Threats to Validity

The record remains active. One tiny two-word challenge, one seed, fixed schedule
ordering, five repetitions, Python verifier overhead, one Windows host, and no
independent replication materially limit the first pilot's external validity.

## Conclusion

Open. No technique is promoted to product architecture until the declared
evidence supports it.

## References

- [Research Evidence And Algorithm
  Mirror](../adr/research-evidence-and-algorithm-mirror.md)
