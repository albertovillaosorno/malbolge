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
