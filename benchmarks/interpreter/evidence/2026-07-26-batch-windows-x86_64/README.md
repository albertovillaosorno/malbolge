# Batch VM Execution Evidence

- Date: 2026-07-26
- Git commit: `5a01c9c49eff264176b35ef2c41a00b6c7a61802`
- Benchmark scope clean at measurement: `true`
- CPU: Intel(R) Xeon(R) CPU E5-2690 v3 @ 2.60GHz
- Physical cores: 12
- Logical processors: 24
- OS: Microsoft Windows 11 Pro 10.0.26200
- Rust: `rustc 1.97.1 (8bab26f4f 2026-07-14)`
- Cargo: `cargo 1.97.1 (c980f4866 2026-06-30)`
- Command: `cargo bench --bench interpreter`
- Historical command note: this command is exact for the recorded commit;
  current HEAD replays the same benchmark logic with
  `cargo run --release --bin interpreter_benchmark`.
- Independent jobs per sample: 96
- Step budget per job: 16
- Samples per implementation: 15

## Results

| Implementation | Median (ns) | Mean (ns) | Min (ns) | Max (ns) | Speedup vs sequential |
|---|---:|---:|---:|---:|---:|
| sequential | 55575400 | 55606927 | 55202600 | 56363200 | 1.00x |
| parallel-1 | 55930200 | 56558253 | 55685100 | 61815500 | 0.99x |
| parallel-2 | 29656900 | 30047680 | 29260100 | 31962100 | 1.87x |
| parallel-4 | 16569700 | 16676860 | 15994100 | 18094300 | 3.35x |
| parallel-8 | 9839800 | 9602187 | 8218200 | 11690500 | 5.65x |

All implementations produced the same deterministic checksum: `17326185397199003045`.

`parallel-1` intentionally exposes host-thread scheduling overhead relative
to the direct sequential baseline. Higher worker counts demonstrate scaling
for this independent 96-job workload on this host; these measurements are
not universal hardware performance claims.

`raw.csv` retains all 75 timing samples and `metadata.json` records the exact
commit, toolchain, host class, workload size, step budget, and cleanliness
of the measured benchmark scope.
