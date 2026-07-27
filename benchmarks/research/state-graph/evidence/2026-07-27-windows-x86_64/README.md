# Exact Current-Profile Checkpoint Cost Evidence

This evidence was captured from commit `2c2365f` using the
canonical `malbolge-2026.2` profile (14 trits, 4,782,969 words). The benchmark
owned/runtime paths matched `HEAD`; unrelated local DOOM/interoperability edits
were present and excluded from the benchmark scope.

## Method

Command:

`.dependencies/jig/source/.dependencies/rust/stable-1.97.1-x86_64-pc-windows-gnu/bin/cargo.exe run --release --bin state_graph_benchmark --quiet`

Each operation has 15 post-warmup samples. Preparation for `insert-exact` and
`replay-exact` occurs outside the timed region:

- `snapshot` measures `ProfileMachine::snapshot_state()`, including the complete
  memory clone;
- `insert-exact` starts from a prepared checkpoint and empty graph, then measures
  full deterministic digest plus first-node insertion;
- `replay-exact` starts from a graph already containing the same state and a
  second prepared checkpoint, then measures full digest plus exact checkpoint
  confirmation.

All 15 samples within each operation produced one deterministic checksum.

## Results

| Operation | Min (ns) | Median (ns) | Max (ns) |
| --- | ---: | ---: | ---: |
| snapshot | 6351000 | 7194700 | 9097100 |
| insert-exact | 26095100 | 26241400 | 26473400 |
| replay-exact | 30439600 | 30756600 | 32390900 |

The exact checkpoint baseline is therefore retained as correctness and
reconstruction evidence, not as the expected per-step state-graph
representation. A production graph needs to avoid repeatedly copying and hashing
all 4,782,969 words while preserving exact collision confirmation.

## Files

- `raw.csv`: all 45 raw timing samples and checksums.
- `metadata.json`: commit, host, toolchain, profile geometry, command, and summary.
