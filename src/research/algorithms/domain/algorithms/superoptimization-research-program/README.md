# Superoptimization research program

This directory is the executable mirror for research ID
`superoptimization-research-program`. The current slice owns a versioned,
validator-enforced experiment plan plus replay-locked deterministic/seeded
candidate schedules and equal-budget verifier-gated execution. It does not yet
define the pilot candidate language, measure elapsed time, or claim a result.

The shared mechanisms live under
`src/research/algorithms/composition/algorithms/superoptimization/`; domain
policy remains here. Stable identities are `deterministic-enumeration-v1`,
`splitmix64-sparse-partial-fisher-yates-v1`, and
`finite-verifier-gated-comparison-v1`. The runner accepts opaque candidate
indices plus a caller-supplied trusted verifier. Future executable comparisons
must preserve challenge identity, budget, baseline, schedule/runner identities,
and the independent verifier boundary.
Regenerable run output belongs in `out/` and remains Git ignored.
