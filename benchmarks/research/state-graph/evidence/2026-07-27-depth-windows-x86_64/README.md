# Persistent Read-Depth Evidence

This evidence was captured post-commit from `51fb0b6` on the
canonical `malbolge-2026.2` profile. Benchmark-owned/runtime paths matched
`HEAD`; unrelated local DOOM/interoperability edits were excluded from the
measured scope.

## Method

`.dependencies/jig/source/.dependencies/rust/stable-1.97.1-x86_64-pc-windows-gnu/bin/cargo.exe run --release --bin state_graph_benchmark --quiet`

Each implementation has 15 post-warmup samples. Sub-microsecond persistent
operations are batched and report the operation count in `raw.csv`; all results
below are normalized to nanoseconds per operation. Patch-chain construction and
input cloning happen outside timed regions.

For each depth, `latest` reads the address changed by the newest patch. `root`
reads an in-range address never changed by any patch and therefore traverses the
entire linked chain before reaching the shared root.

## Read-depth results

| Depth | Latest hit (ns/op) | Root miss (ns/op) | Ops/sample |
| ---: | ---: | ---: | ---: |
| 1 | 17.94 | 18.27 | 16384 |
| 8 | 17.95 | 23.22 | 16384 |
| 64 | 18.02 | 145.47 | 8192 |
| 512 | 18.07 | 1552.39 | 2048 |
| 4096 | 18.75 | 20751.17 | 256 |

Latest-hit latency stays effectively flat through depth 4096. Root-miss latency
is depth-sensitive and reaches 20751.17 ns/op at depth 4096.
A least-squares fit over depths 64, 512, and 4096 gives approximately
5.20 ns of additional root-miss latency per patch for this host/workload.

## Full-checkpoint comparison

| Operation | Median ns/op |
| --- | ---: |
| Snapshot clone | 11467100.00 |
| Exact insert | 27613200.00 |
| Exact replay | 33273300.00 |
| Two-cell persistent apply | 137.98 |
| Latest-patch read | 18.04 |

## Compaction-only lower-bound model

As an illustrative model only, let a full compaction cost at least the measured
snapshot clone `S`, let `alpha` be the fitted root-miss slope, and compact every
`N` patches. Assuming an average root-miss depth of `N/2`, the modeled overhead
is `S/N + misses * alpha * N/2`, before patch application or VM work.

| Root misses/step | Modeled optimum N | Modeled lower bound (ns/step) |
| ---: | ---: | ---: |
| 1 | 2099 | 10925.77 |
| 2 | 1484 | 15451.37 |

This model does **not** establish end-to-end VM throughput. It is used only to
reject unindexed linked patches plus periodic full copying as the sole production
strategy. The next candidate should preserve sharing while making arbitrary reads
bounded independently of patch history depth.

## Files

- `raw.csv`: all raw timing samples, operation counts, and checksums.
- `metadata.json`: commit, host/toolchain identity, normalized summaries, and the
  explicit compaction model above.
