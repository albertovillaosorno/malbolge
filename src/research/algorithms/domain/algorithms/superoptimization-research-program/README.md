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
A fourth comparison, `classic-two-word-prefix-decomposition-v1`, is now
preregistered against the original frozen corpus. It requires exact proof of
suffix independence before any prefix result reuse and keeps its result gate
closed until runner, protocol, and retained provenance are registered.

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
