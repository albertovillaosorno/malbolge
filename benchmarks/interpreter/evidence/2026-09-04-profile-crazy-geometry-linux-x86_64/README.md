# Secondary Linux CPU CRAZY-geometry evidence

This directory retains the N10-N14 `profile-crazy-*` rows emitted by
`interpreter_benchmark` from clean source commit
`fe06b1eead6adbb2b281fa7c5bf7cac566385083` on the repository's secondary Linux
quality-gate host. It is not primary Windows evidence and has no product route
selection authority.

Host: Intel Xeon E5-2690 v3, 12 physical cores / 24 logical processors, Fedora
Linux kernel 7.1.10-200.fc44.x86_64, Rust 1.97.1 with LLVM 22.1.6. Each route has
15 raw samples. Each sample executes 16 complete passes over the same 59,049
pair corpus, and the benchmark verifies scalar/native/padded checksum equality
for each width before timing.

Median nanoseconds are:

| Width | Scalar | Native | Padded | Scalar/native | Scalar/padded |
| --- | ---: | ---: | ---: | ---: | ---: |
| N10 | 127,513,279 | 68,638,975 | 82,851,139 | 1.858x | 1.539x |
| N11 | 140,311,051 | 92,840,228 | 124,393,578 | 1.511x | 1.128x |
| N12 | 150,706,130 | 92,488,900 | 123,592,919 | 1.629x | 1.219x |
| N13 | 162,991,674 | 94,132,729 | 123,403,223 | 1.732x | 1.321x |
| N14 | 174,351,208 | 97,199,554 | 123,557,926 | 1.794x | 1.411x |

Native `5+5+r` has the lowest median at every width on this host. Uniform padded
`5+5+5` also beats scalar at every width, but loses to native. No SIMD route is
present in this harness, so these measurements do not satisfy the SIMD part of
the TODO. Primary Windows evidence and a genuine vectorized implementation also
remain open.
