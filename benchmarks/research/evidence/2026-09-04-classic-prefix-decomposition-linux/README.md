# Classic prefix decomposition - Linux - 2026-09-04

This directory retains the first measured run of the preregistered
`classic-two-word-prefix-decomposition-v1` comparison. The frozen challenge,
fail-closed runner, paired timing protocol, and measurement harness were
committed before measurement at
`ed6825af65aa0fb43ffc3c6dac913fda00b07a52`.

All five repetitions use fixed full-verification-then-decomposed ordering, no
warmup deletion, and a retain-all policy. Both strategies preserve all 8,836
candidate qualities and the same complete quality-map SHA-256
`33d23f934b0541140e51716f6f814d42697773f64788c9f778238c8dc7b64335`.
They retain the same ten accepted candidates and best verified quality one.

The structural result is positive but small. Full verification makes 8,836
independent verifier calls. The proved-prefix strategy structurally discharges
only the 94 candidates in the separately proved `Q` row and makes 8,742 calls,
a reduction of 94 calls (1.064%). Every other prefix still uses full independent
verification.

The host-specific timing result is effectively null. Baseline median strategy
time is 831,921,051 ns with observed range 809,975,223-850,855,502 ns. The
decomposed median is 835,180,632 ns with observed range
818,562,725-970,178,389 ns, 1.004 times the baseline median. Decomposition wins
only two of five paired repetitions, so this run does not support a runtime
speedup claim.

This run is narrow secondary-host evidence from Fedora Linux on an Intel Xeon
E5-2690 v3 with Python 3.14.7. Structural verifier counts and quality-map parity
are exact for the frozen corpus; timing is host-specific. The result does not
justify broadening suffix-independence assumptions or promoting decomposition
as a product optimization.
