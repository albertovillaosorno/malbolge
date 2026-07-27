# Incremental State Identity Evidence

This evidence was captured post-commit from `f317f3e` on the
canonical `malbolge-2026.2` profile. Benchmark-owned/runtime paths matched
`HEAD`; unrelated local DOOM/interoperability edits were excluded from scope.

## Method

`.dependencies/jig/source/.dependencies/rust/stable-1.97.1-x86_64-pc-windows-gnu/bin/cargo.exe run --release --bin state_graph_benchmark --quiet`

Every implementation has 15 post-warmup samples. Incremental operations are
batched at 4096 operations/sample; graph/input preparation occurs outside timed
regions. Full-checkpoint insert/replay retain one operation/sample because each
operation hashes or compares the complete 4,782,969-word state.

## Results

| Operation | Median ns/op |
| --- | ---: |
| Full checkpoint insert | 26292300.00 |
| Full checkpoint replay | 30482800.00 |
| Incremental apply trace | 923.78 |
| Incremental observe new | 535.82 |
| Incremental exact replay | 406.67 |

The measured representation ratios are approximately
49070x for full insert versus
incremental new-state observation and
74958x for full replay versus
incremental replay. Applying one real current trace to the incremental state is
923.78 ns/op on this host/workload.

These are representation microbenchmarks, not end-to-end VM throughput. The
incremental state still stores committed output in a `Vec<u8>`, so an outputting
program can make trace application scale with output history even though memory
and state hashing no longer do.

## Decision

Promote lineage-bound incremental identity as the current state-graph identity
candidate. Retain `ProfileStateGraph` complete checkpoints as the independent
correctness/collision oracle. The next representation risk is append-only output
storage; it should become persistent before native-region graph work treats state
updates as history-size independent.

## Files

- `raw.csv`: all raw timings, operation counts, and deterministic checksums.
- `metadata.json`: commit, host/toolchain identity, summaries, and ratios.
