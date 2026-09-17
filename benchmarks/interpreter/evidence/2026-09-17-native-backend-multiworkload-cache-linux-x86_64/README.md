# Secondary Linux multi-workload native-backend cache evidence

This directory retains release-profile cold-versus-warm backend preparation
measurements from `native_backend_pipeline` at clean producer commit
`7b38e3e42c98da4e0bccfb4cde0636671e242e48`. It covers VM-derived `no-operation/output` and
`rotate/jump-code` two-step traces for both reviewed target ISAs.

Each workload/mode/ISA/scale group retains 15 samples. Warm mode seeds a fresh
direct-artifact cache outside the timer and requires two exact hits per pipeline
iteration with zero timed insertions. Cold mode performs uncached one-step
selection. Both modes retain identical fused admission, COFF emission, and
independent semantic verification after selection.

| Workload | ISA | Scale | Cold ns | Warm ns | Total ratio | Select ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| no-operation-output | x86_64 | 1 | 49,425 | 37,381 | 1.322x | 2.790x |
| no-operation-output | x86_64 | 2 | 97,717 | 72,078 | 1.356x | 2.674x |
| no-operation-output | x86_64 | 4 | 184,406 | 138,739 | 1.329x | 2.561x |
| no-operation-output | aarch64 | 1 | 50,832 | 36,946 | 1.376x | 2.855x |
| no-operation-output | aarch64 | 2 | 98,117 | 71,079 | 1.380x | 2.686x |
| no-operation-output | aarch64 | 4 | 185,650 | 138,223 | 1.343x | 2.650x |
| rotate-jump-code | x86_64 | 1 | 50,868 | 37,904 | 1.342x | 2.789x |
| rotate-jump-code | x86_64 | 2 | 95,942 | 72,905 | 1.316x | 2.673x |
| rotate-jump-code | x86_64 | 4 | 185,444 | 141,121 | 1.314x | 2.577x |
| rotate-jump-code | aarch64 | 1 | 51,049 | 38,090 | 1.340x | 2.809x |
| rotate-jump-code | aarch64 | 2 | 96,021 | 72,317 | 1.328x | 2.701x |
| rotate-jump-code | aarch64 | 4 | 188,300 | 140,966 | 1.336x | 2.653x |

Across all 12 comparisons, warm exact-cache selection has a median
cold-over-warm ratio from 2.561x to 2.855x. End-to-end preparation
ratios range from 1.314x to 1.380x. Admission cold-over-warm ratios
range from 0.997x to 1.028x, keeping the observed gain concentrated
in verified one-step selection rather than fused-admission semantics.

The retained Cargo invocation completed all 360 samples with zero failures in
2.13 s wall time and reached 170,164 KiB maximum resident set size. `raw.csv`
retains every sample, while `metadata.json` binds producer/source/raw hashes,
exact cache invariants, host/toolchain identity, and statistical policy.

Generated code is still not loaded or executed. These measurements therefore
do not support an interpreter-to-native execution speedup claim, and AArch64
rows remain target generation/verification measurements on an x86-64 host.
