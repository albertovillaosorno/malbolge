# Superoptimization research program

This directory is the executable mirror for research ID
`superoptimization-research-program`. The current slice owns a versioned,
validator-enforced experiment plan plus replay-locked deterministic and seeded
candidate-index schedules. It does not yet define the pilot candidate language,
execute the semantic verifier, or claim a measured result.

The shared schedule mechanism lives under
`src/research/algorithms/composition/algorithms/superoptimization/`;
domain policy remains here. Future executable comparisons must preserve the
declared challenge identity, budget, baseline, and independent verifier
boundary.
Regenerable run output belongs in `out/` and remains Git ignored.
