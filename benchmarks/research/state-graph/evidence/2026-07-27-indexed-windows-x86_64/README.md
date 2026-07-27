# Bounded Radix Memory Evidence

This evidence was captured post-commit from `ec459d0` on the
canonical `malbolge-2026.2` profile. The benchmark-owned/runtime paths matched
`HEAD`; unrelated local DOOM/interoperability edits were excluded from scope.

## Method

`.dependencies/jig/source/.dependencies/rust/stable-1.97.1-x86_64-pc-windows-gnu/bin/cargo.exe run --release --bin state_graph_benchmark --quiet`

Every implementation has 15 post-warmup samples. Sub-microsecond operations are
batched and normalized by the explicit `operations` field in `raw.csv`. Radix
histories use distinct override addresses so depth also grows the live overlay,
not merely the number of rewrites to one cell. History construction and input
cloning occur outside timed regions.

## Indexed depth matrix

| Distinct overrides | Latest read (ns/op) | Root fallback (ns/op) | Apply next override (ns/op) | Linked root miss (ns/op) |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 21.39 | 19.73 | 920.17 | 18.44 |
| 8 | 21.43 | 19.92 | 928.30 | 22.90 |
| 64 | 21.19 | 19.97 | 924.34 | 145.87 |
| 512 | 24.02 | 25.78 | 999.02 | 1731.25 |
| 4096 | 24.61 | 20.70 | 1159.62 | 24118.75 |

The four-level radix keeps both override hits and root fallbacks effectively
bounded through 4096 distinct overrides. At depth 4096 the linked-chain root miss
is 24118.75 ns/op while the radix root fallback
is 20.70 ns/op, a measured ratio of
approximately 1165.0x on this host/workload.

## Representation costs

| Operation | Median ns/op |
| --- | ---: |
| Full checkpoint snapshot | 6786500.00 |
| Linked two-cell apply | 139.37 |
| Indexed two-cell apply | 1665.06 |
| Indexed latest read | 21.04 |

The radix pays more per write than the linked list because it path-copies bounded
index nodes. Its measured two-cell apply remains about
4076x below the full snapshot clone
latency, while arbitrary reads no longer inherit patch-history depth.

These are representation microbenchmarks, not end-to-end VM throughput. They do
not yet include exact state hashing/deduplication, graph-edge management, native
execution, or verifier cost.

## Decision

Promote the four-level radix as the next **state-graph memory candidate** for the
current 14-trit profile. Retain the linked patch chain as a correctness oracle and
useful recent-write baseline, not as the general production lookup structure.
The next unresolved problem is exact state identity: deduplication must compare
indexed memories without materializing or hashing all 4,782,969 root words on
every observation.

## Files

- `raw.csv`: all raw samples, operation counts, and checksums.
- `metadata.json`: commit, host/toolchain identity, normalized summaries, and
  derived ratios.
