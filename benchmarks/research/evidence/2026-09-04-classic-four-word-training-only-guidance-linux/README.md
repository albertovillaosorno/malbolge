# Classic four-word training-only guidance - Linux - 2026-09-04

This directory retains the preregistered training-only learned-guidance
comparison from clean source commit
`2d0889ee2eff688d19d8174ffc29f8a230f76caf`. The three-word training corpus,
model equation, fitted-weight digest, static and learned schedule digests, and
100,000-candidate four-word holdout were fixed before holdout outcomes.

The holdout characterization found zero accepted candidates. Consequently both
strategies exhaust the common 50,000-evaluation ceiling in all five repetitions,
with no candidate or quality. The primary first-hit ranking hypothesis is
therefore inconclusive on this exact holdout and cannot support learned guidance.
The null outcome is retained rather than replacing the challenge post-hoc.

Static end-to-end median time is 407,894,273 ns with observed range
400,226,527-461,588,241 ns. Learned training alone has median 6,259,721,192 ns
(range 6,045,943,284-7,483,139,893 ns). Learned schedule-plus-search has median
2,092,124,024 ns (range 2,044,123,502-2,240,697,649 ns), and learned end-to-end
median is 8,303,844,694 ns (range 8,138,067,308-9,723,837,542 ns).

The learned/static end-to-end median ratio is 20.358x, with zero of five learned
timing wins. These timing observations are secondary because neither arm can
find a solution on the frozen holdout. They do show that this Python training
and materialized learned schedule are not a runtime optimization. No product
promotion or broader learned-guidance rejection is inferred from one null
holdout.
