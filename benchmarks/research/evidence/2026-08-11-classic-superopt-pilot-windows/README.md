# Classic superoptimization pilot — Windows — 2026-08-11

This directory retains the first measured run of the preregistered
`classic-verified-block-search-v1` comparison. The implementation and timing
protocol were committed before measurement at
`23dd86d656e6b7bdd0d1422a984e95a9feeebd0f`.

All five repetitions use the same complete 8,836-candidate classic corpus,
seed-zero schedule identity, independent semantic verifier, 60-second wall
bound, 10,000-evaluation bound, fixed enumeration-then-seeded order, no warmup,
and retain-all policy. Both schedules exhaust the corpus and verify the same ten
accepted candidates in every repetition. Both reach best quality 1.

Deterministic enumeration reaches its first verified candidate at evaluation
706 in every repetition; the seeded SplitMix64 order reaches one at evaluation
250. Median first-hit elapsed time is 18,506,300 ns for enumeration and
6,119,900 ns for the seeded order. Median full-corpus elapsed time is
227,928,500 ns versus 227,433,600 ns, with overlapping observed ranges
(221,533,800–248,096,000 ns versus 222,662,100–284,910,800 ns).

The evaluation-count result is exact for this frozen corpus and schedule. The
wall-time samples are host-specific pilot evidence only. Fixed schedule ordering,
one seed, five repetitions, Python verifier overhead, and the deliberately tiny
two-word challenge limit external validity. In particular, the nearly equal
full-corpus medians do not support a general throughput advantage. The
preregistered plan names dispersion as `observed-range`; benchmark protocol v1
serializes the same min/max interval under its `min-max` dispersion vocabulary
and keeps `observed-range` as the uncertainty method.
