# Dependency-region benchmark evidence

This directory records post-commit timing evidence for verified dependency-region
reuse on commit `1988f14`. The benchmark uses canonical profile
`malbolge-2026.2`, a region budget of 8 semantic steps, and
15 samples per operation.

## Result

- exact entry guard hit: 60.57 ns/op;
- dependency guard hit: 106.88 ns/op;
- dependency guard miss: 72.22 ns/op;
- verified dependency shortcut: 6.88 microseconds/op;
- prepared direct normative region run: 889.60 microseconds/op;
- normative certificate verification: 8.78 ms/op.

The dependency guard is 1.76x the exact-guard hit latency, but it admits
states that differ only in memory outside the verified live-in set. The verified
shortcut is about 129.36x faster than the prepared direct VM region run on
this host. This is a region-reuse microbenchmark, not an end-to-end native-tier
speedup claim.

`raw.csv` is the raw sample set. `metadata.json` records commit, toolchain, host,
checksums, operation counts, and derived ratios. Benchmark-owned/runtime paths
matched the recorded commit; unrelated local DOOM interoperability edits were
excluded from the measured scope.
