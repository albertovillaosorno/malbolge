# Exact Region Guard Evidence

This evidence was captured post-commit from `f16785d` for the
canonical current profile. Benchmark-owned/runtime paths matched `HEAD`; unrelated
local DOOM/interoperability edits were excluded from scope.

## Method

`.dependencies/jig/source/.dependencies/rust/stable-1.97.1-x86_64-pc-windows-gnu/bin/cargo.exe run --release --bin state_graph_benchmark --quiet`

Each case has 15 post-warmup samples. Exact guard hit/miss operations are batched
at 16,384 operations per sample. Certificate verification remains one operation
per sample because it deliberately materializes the entry checkpoint and
re-executes the normative profile VM.

## Results

| Operation | Median ns/op |
| --- | ---: |
| Exact entry guard hit | 55.51 |
| Exact entry guard miss | 59.09 |
| Normative certificate verify | 9092700.00 |

The verifier is approximately 163799x the exact
guard-hit latency in this microbenchmark. This asymmetry is intentional: verifier
work is cold/untrusted promotion work, while exact guard evaluation is the hot
reuse path.

## Decision

Keep exact-state equality as the first native-region runtime guard. At about
55--60 ns on this host/workload, reducing the guard is **not** justified primarily
for guard latency. The reason to derive dependency/read-set guards is to increase
safe region reuse across states that differ only in future-irrelevant memory, not
to rescue an expensive exact guard.

Certificate verification remains normative and expensive by design. No benchmark
result is permission to replace verifier replay with hashes or heuristic trust.

## Files

- `raw.csv`: all raw timings, operation counts, and deterministic checksums.
- `metadata.json`: commit/host/toolchain identity and normalized summaries.
