# Secondary Linux three-workload native-backend cache evidence

This directory retains release-profile cold-versus-warm backend preparation
measurements from `native_backend_pipeline` at clean producer commit
`2feb6c985b07e8987ddec1ca5845155229fa0e0e`. It covers VM-derived `crazy/crazy`,
`no-operation/output`, and `rotate/jump-code` two-step traces for both reviewed
target ISAs.

Each workload/mode/ISA/scale group retains 15 samples. Warm mode seeds a fresh
direct-artifact cache outside the timer and requires two exact hits per pipeline
iteration with zero timed insertions. Cold mode performs uncached one-step
selection. Both modes retain identical fused admission, COFF emission, and
independent semantic verification after selection.

| Workload | ISA | Scale | Cold ns | Warm ns | Total ratio | Select ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| crazy-pair | x86_64 | 1 | 49,784 | 37,532 | 1.326x | 2.759x |
| crazy-pair | x86_64 | 2 | 94,780 | 71,338 | 1.329x | 2.643x |
| crazy-pair | x86_64 | 4 | 187,473 | 140,567 | 1.334x | 2.543x |
| crazy-pair | aarch64 | 1 | 51,886 | 37,312 | 1.391x | 2.881x |
| crazy-pair | aarch64 | 2 | 95,846 | 71,857 | 1.334x | 2.706x |
| crazy-pair | aarch64 | 4 | 194,537 | 138,233 | 1.407x | 2.654x |
| no-operation-output | x86_64 | 1 | 46,618 | 35,623 | 1.309x | 2.740x |
| no-operation-output | x86_64 | 2 | 90,231 | 71,185 | 1.268x | 2.592x |
| no-operation-output | x86_64 | 4 | 176,220 | 136,448 | 1.291x | 2.516x |
| no-operation-output | aarch64 | 1 | 47,660 | 35,705 | 1.335x | 2.802x |
| no-operation-output | aarch64 | 2 | 92,588 | 70,762 | 1.308x | 2.618x |
| no-operation-output | aarch64 | 4 | 179,652 | 137,320 | 1.308x | 2.556x |
| rotate-jump-code | x86_64 | 1 | 48,268 | 37,194 | 1.298x | 2.751x |
| rotate-jump-code | x86_64 | 2 | 95,743 | 72,416 | 1.322x | 2.699x |
| rotate-jump-code | x86_64 | 4 | 186,973 | 147,576 | 1.267x | 2.571x |
| rotate-jump-code | aarch64 | 1 | 49,677 | 37,102 | 1.339x | 2.864x |
| rotate-jump-code | aarch64 | 2 | 95,717 | 72,224 | 1.325x | 2.676x |
| rotate-jump-code | aarch64 | 4 | 189,371 | 145,132 | 1.305x | 2.611x |

Across all 18 comparisons, warm exact-cache selection has a median
cold-over-warm ratio from 2.516x to 2.881x. End-to-end preparation
ratios range from 1.267x to 1.407x. Admission cold-over-warm ratios
range from 0.984x to 1.018x, keeping the observed gain concentrated
in verified one-step selection rather than fused-admission semantics.

The retained Cargo invocation completed all 540 samples with zero failures in
3.00 s wall time and reached 170,468 KiB maximum resident set size. `raw.csv`
retains every sample, while `metadata.json` binds producer/source/raw hashes,
exact cache invariants, host/toolchain identity, and statistical policy.

Generated code is still not loaded or executed. These measurements therefore
do not support an interpreter-to-native execution speedup claim, and AArch64
rows remain target generation/verification measurements on an x86-64 host.
