# Classic three-word initial-decode heuristic - Linux - 2026-09-04

This directory retains the first measured run of
`classic-three-word-initial-halt-heuristic-v1`. The holdout experiment was
preregistered before challenge execution at source commit `f92a6ef4`. The
challenge, static schedule, verifier-gated runner, and five-pair timing protocol
were all committed before measurement at
`b399fff7bd1904d60dde274f940b5d2c68906824`.

The frozen holdout contains all 830,584 graphical three-byte classic sources.
Its independently checked verifier accepts 86 candidates that halt without
prior I/O within three transitions: 64 quality-one, 16 quality-two, and six
quality-three candidates. The comparison evaluates exactly 50,000 unique
candidates per strategy in every retained repetition.

Natural enumeration finds no verified candidate within the 50,000-evaluation
budget in any of the five repetitions. The preregistered static heuristic finds
its first verified candidate at evaluation 475, candidate index 424,602, and its
50,000-candidate prefix contains all 86 accepted holdout candidates with best
quality one. This supports the primary first-hit search-order hypothesis on the
frozen three-word holdout.

The full strategy timing result moves in the opposite direction because the
registered timing scope includes schedule construction. Baseline median elapsed
time is 215,984,447 ns with observed range 209,487,992-233,148,571 ns. The
heuristic median is 2,948,297,136 ns with observed range
2,763,390,294-3,298,160,067 ns, about 13.651 times the baseline median. The
heuristic wins zero of five elapsed-time pairs.

The result therefore supports the static feature as a search-order signal but
not this materialized full-corpus sort as a faster implementation. A later
engineering or research slice may test an equivalent bucketed/lazy schedule,
but it must preserve the same feature and verifier boundary rather than hiding
schedule-construction cost post hoc. This single-host Python result does not
establish generalization to larger source lengths or other objective families.
