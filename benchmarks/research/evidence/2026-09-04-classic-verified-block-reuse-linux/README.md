# Classic verified-block reuse - Linux - 2026-09-04

This directory retains the first measured run of the preregistered
`classic-two-pass-verified-block-reuse-v1` comparison. The two-pass challenge,
fail-closed runner, and five-pair timing protocol were committed before
measurement at `f42579b927b79d62d3763d4ee714ed22961d80b2`.

The workload is deliberately exact and repetitive: it executes two complete
lexicographic passes over the same frozen 8,836-candidate classic corpus. The
baseline independently verifies all 17,672 requests. The reuse strategy verifies
each exact candidate index once, then serves the second identical occurrence
from an in-run cache. It therefore makes 8,836 verifier calls and reuses 8,836
requests, a 50% reduction in independent verifier work.

Every retained row has the same complete request-quality-map SHA-256
`9dfe349bf961baf7c0f507fcff549198a3dffe687b1ea23714769e9105f36fdd`,
20 accepted requests, and best verified quality one. Cache identity is the exact
frozen candidate index; no semantic equivalence across distinct candidates is
assumed.

All five fixed-order paired repetitions favor reuse. Baseline median strategy
time is 1,617,672,749 ns with observed range
1,611,357,982-1,733,219,224 ns. Reuse median is 851,323,429 ns with observed
range 824,892,050-866,041,992 ns. The median baseline/reuse ratio is 1.900x.

This supports exact verified-result reuse for a workload where the second pass
is known to be identical. It does not estimate cache hit rate, reuse distance,
invalidation cost, persistent catalogue behavior, or benefit on novel compiler
workloads. The fixed baseline-then-reuse order and Python verifier overhead are
additional threats to timing interpretation. Product promotion remains outside
this research record.
