# Crazy preimage pruning — Windows — 2026-08-12

This directory retains the first measured run of the preregistered
`classic-crazy-exact-preimage-pruning-v1` comparison. The frozen 12-problem
challenge, structural runner, paired timing protocol, and measurement harness
were committed before measurement at
`5fbea3461d5fbb035611b1ce6cce43b3d4cad44c`.

All five repetitions use fixed full-domain-then-exact ordering, no warmup
deletion, and a retain-all policy. Both strategies produce 2,047 total exact
preimages and the same canonical semantic SHA-256
`86cbd11391b4db60a8665cb2f1d698140206f388400bd072116d72a32cbf2f62`.

The structural result is positive and exact for the frozen challenge. Complete
classic enumeration checks 708,588 data candidates across the twelve problems,
while the exact digitwise projection checks 2,047, eliminating 706,541 candidate
checks (99.71%) without changing any complete independent preimage set.

The host-specific timing result is negative. Full-domain median strategy time is
2,298,684,800 ns with observed range 2,122,264,300–2,474,458,100 ns. Exact
projection median time is 2,931,140,300 ns with observed range
2,234,618,200–3,064,837,900 ns, about 1.28 times the baseline median. The ranges
overlap. On this Python implementation and host, exact projection/preparation
overhead outweighs the eliminated independent candidate checks in elapsed time.
No runtime-speedup claim is supported by this run.

This run is deliberately narrow. It uses one cardinality-spanning synthetic
classic challenge, one host, fixed baseline-first ordering, five paired
repetitions, and Python implementation overhead. Candidate counts and semantic
set equality are exact for the frozen challenge; timing is host-specific
evidence
only and does not establish a general performance loss or gain for compiled or
accelerated optimizer implementations.
