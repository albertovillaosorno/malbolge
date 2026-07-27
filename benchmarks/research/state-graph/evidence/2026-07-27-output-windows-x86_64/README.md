# Persistent Output Append Evidence

This evidence was captured post-commit from `1d229d0`. The
benchmark-owned/runtime paths matched `HEAD`; unrelated local DOOM/interoperability
edits were excluded from scope.

## Method

`.dependencies/jig/source/.dependencies/rust/stable-1.97.1-x86_64-pc-windows-gnu/bin/cargo.exe run --release --bin state_graph_benchmark --quiet`

Every case has 15 post-warmup samples. History construction is outside timed
regions. The baseline reproduces the previous state-update behavior by copying the
complete existing output bytes into a fresh `Vec<u8>` and pushing one byte. The
candidate clones the persistent history handle during preparation and appends one
immutable tail node inside the timed operation.

## Results

| Existing output bytes | Vec clone + push (ns/op) | Persistent append (ns/op) | Vec / persistent |
| ---: | ---: | ---: | ---: |
| 0 | 84.45 | 107.70 | 0.8x |
| 1024 | 230.60 | 139.82 | 1.6x |
| 65536 | 3124.61 | 138.87 | 22.5x |
| 262144 | 20827.34 | 144.53 | 144.1x |

The persistent representation pays small fixed overhead for an empty history, but
append latency remains effectively flat through 256 KiB while complete-vector
copying scales with existing output length. At 256 KiB the measured ratio is
about 144x on this host/workload.

The benchmark measures append representation cost only. Materialization remains
an oracle/serialization operation, and exact equality between non-shared branches
may walk output tails after digest/length filters. Ordinary replay sharing uses a
tail pointer shortcut.

## Decision

Promote persistent output storage for incremental state identity. This removes the
last obvious history-length copy from ordinary state updates. The next state-graph
research slice should focus on native-region safety/guards and further semantic
mutation-history collapse rather than another storage representation.

## Files

- `raw.csv`: raw timings, operation counts, and checksums.
- `metadata.json`: commit/host/toolchain identity and normalized comparisons.
