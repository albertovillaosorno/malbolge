# CPU Benchmark Evidence

This directory owns deliberately retained modern CPU microbenchmark evidence.
It is separate from `benchmarks/interpreter/`, which owns historical
interpreter evidence. CPU benchmark results are research/performance
observations only; they do not define VM semantics or select product routes by
themselves.

Tracked evidence must identify its clean source commit, host/toolchain,
workload, validation boundary, timing method, raw samples, and whether it has
product selection authority. Regenerable scratch output remains under `.temp`
or another ignored local-output surface unless a reviewed result is
intentionally retained.
