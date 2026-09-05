# Superoptimization research program

This directory is the executable mirror for research ID
`superoptimization-research-program`. The current slice owns a versioned,
validator-enforced experiment plan plus replay-locked deterministic/seeded
candidate schedules and equal-budget verifier-gated execution. The pilot now
binds the complete 8,836-member two-graphical-byte classic corpus to
`classic-two-word-no-io-halt-v1`, which accepts exact one- or two-transition
halts without prior I/O and scores transitions to halt. The first measured
seed-zero pilot is now retained under `benchmarks/research/evidence/` with five
cold, retain-all repetitions from pre-run commit `23dd86d6`. Seeded ordering
reaches the first verified candidate in 250 evaluations versus 706 for natural

enumeration; both schedules find all ten accepted candidates and best quality 1.
The host-specific timing evidence does not establish a general throughput win.
A later preregistered seeds-0-through-7 work-count replication is also retained.
Four seeded schedules reach verification before enumeration's evaluation 706 and
four reach it later; seeded median first-hit work is 723. This mixed/null result

weakens the seed-zero first-hit conclusion. Replication timing is retained only
as provenance and is not interpreted. A second technique,
`classic-history-residue-canonicalization-v1`, now has a retained measurement.
Its exact residue substrate requires stable address identity and no intervening
write, and callers inject the classic encryption successor rather than granting
the optimizer semantic authority. The frozen 10,000-observation challenge and

comparison runner preserve one exact per-observation semantic digest. Across the
retained five paired repetitions, residue identity reduces unique states and
independent verifier calls from 10,000 to 6,496 (35.04%). Host timing is
negative: raw-state median strategy time is 96,384,900 ns versus 244,447,500 ns
for canonicalized state, about 2.54 times slower. This supports the structural
state-reduction claim only; it does not support a runtime-speedup claim. A
third technique now has a preregistered retained comparison:
`classic-crazy-exact-preimage-pruning-v1` compares the existing
`classic-crazy-digitwise-exact-preimage-v1` preparer with complete 59,049-word

data enumeration for fixed classic accumulator/target problems. Its 12-problem
challenge spans unreachable through 1,024-preimage classes and preserves exact
independent preimage-set equality. Candidate work falls from 708,588 checks to
2,047 (99.71%), but the retained Windows/Python median rises from
2,298,684,800 ns to 2,931,140,300 ns, about 1.28 times slower. Observed timing

ranges overlap. The run supports exact pruning but not a runtime-speedup claim.

A fourth comparison, `classic-two-word-prefix-decomposition-v1`, now has a
retained five-pair Linux measurement from source commit `ed6825af`. Its
fail-closed runner reuses only separately proved prefix classes, fully verifies
every other candidate, and preserves the complete candidate-quality map.

The sole proved `Q` row removes 94 independent verifier calls: 8,836 fall to
8,742, a 1.064% reduction. Host timing is effectively null: baseline median is
831,921,051 ns versus 835,180,632 ns decomposed, and decomposition wins only two
of five pairs. This supports the small exact work reduction, not a runtime
speedup claim.

A fifth comparison, `classic-two-pass-verified-block-reuse-v1`, now has a
retained five-pair Linux measurement from source commit `f42579b9`. The baseline
verifies 17,672 requests across two complete corpus passes; exact
candidate-index
reuse verifies 8,836 unique candidates once and reuses all 8,836 second-pass
requests while preserving the complete request-quality map.

Median strategy time falls from 1,617,672,749 ns to 851,323,429 ns, a 1.900x
baseline/reuse ratio, and reuse wins all five paired repetitions. The workload
has deliberate 100% second-pass repetition, so this supports exact reuse under
that condition rather than a production cache-hit-rate or invalidation claim.

A sixth comparison, `classic-three-word-initial-halt-heuristic-v1`, now has a
retained Linux holdout measurement. Under the fixed 50,000-evaluation budget,
natural enumeration finds no verified candidate, while the preregistered static
initial-decode order first verifies at evaluation 475 and includes all 86
accepted three-word candidates with best quality one. The ordering result is
positive, but full strategy timing is negative: median elapsed time rises from
215,984,447 ns to 2,948,297,136 ns because the registered scope includes
materializing and sorting the 830,584-candidate schedule. The feature is
retained
as a search signal; the current sorting implementation is not a runtime win.

A seventh comparison, `classic-four-word-training-only-guidance-v1`, freezes
its complete three-word training corpus, pooled initial-decode model, and both
50,000-candidate order prefixes before executing a new four-word holdout. The
100,000-candidate holdout excludes exact training-positive three-byte prefixes
and then retains a valid null characterization: it contains zero accepted
candidates. A known excluded extension, `Q&%$`, still verifies at quality one,
so the null is not explained by a verifier that cannot accept.

The retained five-pair run records `no-solution` for both static and learned
orders at the common 50,000-evaluation ceiling. Static end-to-end median time is
407,894,273 ns, while learned end-to-end median time is 8,303,844,694 ns;
training alone has median 6,259,721,192 ns. The primary first-hit hypothesis is
therefore inconclusive on this holdout, and the current Python learned path is
not a runtime optimization. A later learned challenge must receive a new
identity rather than replacing this negative evidence.

A low-level structural regression proves only the `Q` prefix so far: entry halts
before encryption, and exactly eight load-admitted suffixes have quality one.
The runner therefore treats only that 94-suffix row structurally; every other
prefix remains a full-verification case until separately proved.

The shared mechanisms live under
`src/research/algorithms/composition/algorithms/superoptimization/`; domain
policy remains here. Stable identities are `deterministic-enumeration-v1`,
`splitmix64-sparse-partial-fisher-yates-v1`, and
`finite-verifier-gated-comparison-v1`, and
`finite-verifier-gated-dual-bound-comparison-v1`. The runners accept opaque
candidate indices plus a caller-supplied trusted verifier; the dual-bound path
also accepts an injected monotonic nanosecond clock and records which declared
stopping bound fired. `superoptimization-run-record-v1` can then render a
candidate schema-v1 run manifest only from the frozen plan, that bounded result,
and caller-supplied exact provenance; rendering writes no evidence, does not
invent host/toolchain/workload identity, and rejects candidate-count or workload
hash drift from the frozen plan. `pilot.py` revalidates that plan against the
concrete challenge before creating the dual-bound request or wiring its

verifier. `measurement.py` retains the frozen five-repetition series and
`superoptimization-measurement-run-record-v1` binds every repetition to one
tracked run identity before raw evidence is promoted.
Future executable comparisons must
preserve challenge identity, budget, baseline, schedule/runner identities, and
the independent verifier boundary. Regenerable run output belongs in `out/` and
remains Git ignored.

A preregistered stop-on-first follow-up preserves the exact bucketed heuristic
order while changing only the stopping policy. On the same known three-word
workload, natural enumeration exhausts 50,000 evaluations with no hit, while
the heuristic reproduces candidate 424,602 at evaluation 475 with quality one.
Median elapsed time is 212,739,774 ns baseline versus 13,146,086 ns heuristic,
a 16.183x baseline/heuristic ratio with five of five heuristic wins. This is a
post-holdout implementation result and does not erase the earlier negative
full-budget timing.

## Bounded comparative conclusion

The acceptance-required comparison matrix is complete and machine-readable in
`comparative-conclusion.toml`. Decomposition, verified-result reuse,
canonicalization, exact pruning, static heuristic search, and training-only
learned guidance all resolve to retained source-pinned evidence. Results are
mixed by design: exact work reductions do not consistently become host-time
wins, the positive reuse result assumes complete second-pass repetition, the
static heuristic has a positive first-hit signal, and the learned four-word
holdout is a retained no-solution result. No row grants product authority.
