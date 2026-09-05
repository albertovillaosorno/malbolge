# Secondary Linux AVX2 CRAZY geometry v2 evidence

This directory retains the clean `cpu-profile-crazy-avx2-v2` run from source
commit `76104c08990994ce88bc58570607f1f18d7f3bc4`. The host is the secondary
Linux quality gate: Intel Xeon E5-2690 v3, 12 physical / 24 logical processors,
Fedora Linux kernel 7.1.10-200.fc44.x86_64, with pinned Clang 22.1.8. This
evidence has no product route-selection authority.

Version 2 preserves the wrapping-u32 59,049-pair corpus, 16 complete corpus
repetitions per sample, 15 samples per implementation, rotating route order,
and complete scalar-tritwise output validation before timing. It extends the
v1 N10-N14 matrix with N15 as arithmetic-only evidence. N15 is three complete
five-trit chunks, requires no semantic projection, and does not admit a runtime
profile. Its repeated checksum is `4,726,060,935,024`.

Pinned-Clang assembly contains three `vpgatherdd` instructions and AVX2 YMM
arithmetic. All 270 raw timing samples are retained.

| Width | Scalar lookup median | AVX2 lookup median | Scalar/AVX2 | AVX2 paired wins |
| --- | ---: | ---: | ---: | ---: |
| N10 | 6,272,158 ns | 4,702,211 ns | 1.334x | 15/15 |
| N11 | 15,904,580 ns | 9,384,736 ns | 1.695x | 15/15 |
| N12 | 15,970,617 ns | 9,386,911 ns | 1.701x | 15/15 |
| N13 | 15,820,432 ns | 9,383,050 ns | 1.686x | 15/15 |
| N14 | 15,825,825 ns | 9,342,688 ns | 1.694x | 15/15 |
| N15 | 11,547,865 ns | 5,756,478 ns | 2.006x | 15/15 |

The N15 result is consistent with removing the N11-N14 semantic projection
step from an otherwise uniform three-chunk implementation, but this benchmark
does not isolate projection cost from every other generated-code effect. The
intervals use C23 `timespec_get(TIME_UTC)`, not cycle counters. Primary Windows
CPU/SIMD evidence and the separate CUDA cache/selection blockers remain open,
so this result does not promote a product geometry.
