# Classic three-word first-hit follow-up - Linux - 2026-09-04

This directory retains a preregistered implementation follow-up to the earlier
three-word holdout comparison. The follow-up plan, exact bucketed schedule, and
stop-on-first runner were committed before this timing run at `a80ee1cf674fd62ef1bd8b45985f550014ce6af1`.
It reuses the already characterized holdout and therefore is not an independent
holdout confirmation.

Natural enumeration has no verified hit within its 50,000-evaluation ceiling in
all five repetitions. Its median elapsed time is 212,739,774 ns with observed
range 206,582,814-253,086,582 ns. The bucketed heuristic reaches the retained
first verified candidate, index 424,602 with quality one, after 475 evaluations
in every repetition. Its median is 13,146,086 ns with observed range
12,635,046-14,932,775 ns.

The median baseline/heuristic ratio is 16.183x and the heuristic wins all five
paired timing repetitions. Schedule construction remains inside both timed
strategy calls. This supports the bucketed heuristic specifically for a
stop-on-first policy on this known three-word workload; it does not revise the
separately retained negative full-budget timing or establish larger-corpus
generalization.
