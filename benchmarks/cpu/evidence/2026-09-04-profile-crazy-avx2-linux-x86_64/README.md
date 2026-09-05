# Secondary Linux AVX2 CRAZY-geometry evidence

This directory retains the clean `cpu-profile-crazy-avx2-v1` run from source
commit `e09d51d16ed7eaeee2156899b7d913670a33fd5d`. The host is the secondary Linux
quality gate: Intel Xeon E5-2690 v3, 12 physical / 24 logical processors, Fedora
Linux kernel 7.1.10-200.fc44.x86_64, with pinned Clang 22.1.8. This evidence has
no product route-selection authority.

The benchmark uses the same wrapping-u32 59,049-pair corpus and 16 repetitions
per sample as the Rust CPU CRAZY geometry benchmark. It records 15 samples for
scalar tritwise, scalar padded lookup, and eight-lane AVX2 padded lookup at each
N10-N14 width. Before timing, every padded and AVX2 result is compared with the
independent scalar result, and the repeated checksum must equal the existing
Rust benchmark checksum. Pinned-Clang assembly contains three `vpgatherdd`
instructions and AVX2 YMM arithmetic for the SIMD path.

| Width | Scalar padded median | AVX2 padded median | Scalar/AVX2 | AVX2 paired wins |
| --- | ---: | ---: | ---: | ---: |
| N10 | 6,103,260 ns | 4,584,882 ns | 1.331x | 15/15 |
| N11 | 14,992,499 ns | 9,288,631 ns | 1.614x | 15/15 |
| N12 | 14,391,326 ns | 9,240,532 ns | 1.557x | 14/15 |
| N13 | 15,139,031 ns | 9,261,840 ns | 1.635x | 15/15 |
| N14 | 15,285,523 ns | 9,312,114 ns | 1.641x | 14/15 |

Thus AVX2 is beneficial for this padded microkernel on this secondary host at
all five measured widths. The intervals use C23 `timespec_get(TIME_UTC)`; they
are not hardware-cycle measurements. Primary Windows evidence and the separate
CUDA cache/selection blockers remain open, so this result does not promote a
product geometry.
