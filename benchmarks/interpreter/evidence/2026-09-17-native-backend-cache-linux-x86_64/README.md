# Secondary Linux native-backend cache evidence

This directory retains release-profile cold-versus-warm backend preparation
measurements from `native_backend_pipeline` at clean producer commit
`084b50a1ab6149b387455f0c43f5f07772098b40`. The workload is the same
VM-derived current-profile `rotate/jump-code` two-step trace used by the earlier
pipeline evidence.

Each group retains 15 samples. Cold mode performs uncached one-step selection;
warm mode seeds a fresh direct-artifact cache outside the timer and requires
two exact hits per pipeline iteration with zero timed insertions. Both modes
perform the same fused admission, COFF emission, and semantic verification.

| ISA | Scale | Cold ns | Warm ns | Total ratio | Select ratio |
| --- | ---: | ---: | ---: | ---: | ---: |
| x86_64 | 1 | 51,149 | 39,089 | 1.309× | 2.678× |
| x86_64 | 2 | 97,351 | 74,590 | 1.305× | 2.606× |
| x86_64 | 4 | 193,555 | 147,612 | 1.311× | 2.660× |
| aarch64 | 1 | 52,232 | 37,575 | 1.390× | 2.885× |
| aarch64 | 2 | 99,758 | 74,002 | 1.348× | 2.720× |
| aarch64 | 4 | 195,191 | 146,159 | 1.335× | 2.656× |

Across these six comparisons, warm exact-cache selection has a median
cold-over-warm ratio from 2.606× to 2.885×. End-to-end preparation ratios
range from 1.305× to 1.390× because fused admission, emission, and independent
verification remain in both modes. Admission medians differ by less than 3%.

The retained Cargo invocation completed all 180 samples with zero failures in
10.88 s wall time and reached 588,620 KiB maximum resident set size.
`raw.csv` retains every sample, while `metadata.json` binds producer/source/raw
hashes, exact cache invariants, host/toolchain identity, and statistical policy.

Generated code is still not loaded or executed. These measurements therefore
do not support an interpreter-to-native execution speedup claim, and AArch64
rows remain target generation/verification measurements on an x86-64 host.
