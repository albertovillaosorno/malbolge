# History-residue canonicalization — Windows — 2026-08-12

This directory retains the first measured run of the preregistered
`classic-history-residue-canonicalization-v1` comparison. The frozen challenge,
runner, paired timing protocol, and measurement harness were committed before
measurement at `9ff4834614b35900cbc51f85a4edd3b5e24fe38b`.

All five repetitions run the same 10,000-observation corpus in fixed
raw-then-canonicalized order, with no warmup deletion and a retain-all policy.
Both strategies produce the same exact per-observation semantic SHA-256
`fd3644058b415d3acc091d0b837111948ff640132f7c8093fca562d553bdb527`.

The structural result is positive: raw visit-count identity uses 10,000 unique
search states and independent verifier calls, while exact history residues use
6,496, a reduction of 3,504 (35.04%). Generated successors remain 10,000 for
both strategies.

The host-specific timing result is negative. Raw-state median strategy time is
96,384,900 ns with observed range 84,090,300–106,369,300 ns. Canonicalized
median time is 244,447,500 ns with observed range
202,653,700–268,365,700 ns, about 2.54 times the raw median. On this Python
implementation and host, the exact residue computation costs more wall time than
it saves through fewer semantic-verifier calls. No runtime-speedup claim is

supported by this run.

This run is deliberately narrow. It uses one deterministic synthetic history
corpus, one host, fixed raw-first ordering, five paired repetitions, and Python
implementation overhead. The structural state/verifier counts are exact for the
frozen corpus; timing is host-specific evidence only and does not establish a
general performance loss or gain for a compiled optimizer implementation.
