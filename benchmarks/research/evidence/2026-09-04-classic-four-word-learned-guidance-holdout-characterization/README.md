# Classic four-word learned-guidance holdout characterization

This retained characterization was produced from clean source commit
`4cd77739c3bbee222487ab54a34b421bef4881ee`, after the training-only model and
both candidate-order prefixes were content-pinned and before comparative timing.

The frozen holdout contains 100,000 deterministically selected graphical
four-byte candidates. Exact bounded verification found **zero accepted
candidates**. `accepted.csv` therefore contains only its header; the canonical
ordinal/quality accepted-set SHA-256 is the SHA-256 of empty bytes:
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.

This is retained as a valid null challenge characterization. It means neither
static nor learned order can achieve the preregistered first-hit objective on
this exact holdout. It does not show that the four-step verifier is incapable of
acceptance: regression evidence separately checks the known training-positive
prefix extension `Q&%$`, which verifies at quality one but is intentionally
excluded by the preregistered holdout selection rule.

The holdout is not redesigned after this observation. Any later learned-guidance
challenge must receive a new identity and preregistration rather than replacing
this null result.
