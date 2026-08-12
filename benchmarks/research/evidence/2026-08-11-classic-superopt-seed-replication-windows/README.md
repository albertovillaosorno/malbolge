# Classic superoptimization seed replication — Windows — 2026-08-11

This retained replication tests whether the seed-zero first-hit evaluation-work
advantage survives the preregistered seeds 0 through 7. The challenge, verifier,
candidate corpus, evaluation bound, and wall-clock bound are unchanged from the
frozen classic pilot. Commit `f2dcc67a` already contained the replication plan
before any seed 1 through 7 result was observed.

Deterministic enumeration reaches its first verified candidate at evaluation 706
for every trial. Seeded first-hit evaluations are 250, 1709, 642, 1142, 189,
1861, 506, and 804 for seeds 0 through 7. Four seeds improve on enumeration and
four are worse. The seeded median is 723 evaluations, versus 706 for enumeration.
Every schedule exhausts all 8,836 candidates, verifies the same ten accepted
sources, and retains best quality 1.

This is a mixed/null replication result that materially weakens the seed-zero
first-hit-work conclusion. The retained elapsed nanoseconds are provenance only;
this replication preregistered no timing comparison. The result remains limited
to one tiny two-word classic challenge and one host.
