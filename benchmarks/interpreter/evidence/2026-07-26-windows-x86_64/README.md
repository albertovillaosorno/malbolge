# CPU VM Table Optimization Evidence

- Date: 2026-07-26
- Git commit: `888b4923c4c5f56c01e2447229dd02b6a938dfbd`
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
- Samples per implementation: 15
- Crazy repetitions per sample: 16 full 59,049-word passes
- Rotate repetitions per sample: 128 full 59,049-word passes

## Results

| Operation | Scalar median (ns) | Table median (ns) | Median speedup |
|---|---:|---:|---:|
| crazy | 77456700 | 7423600 | 10.43x |
| rotate | 15260300 | 10141700 | 1.50x |

Checksums are identical between scalar and table implementations for each
operation. `raw.csv` retains every timing sample and `metadata.json` records
the exact commit, command, toolchain, and benchmark host class.

These measurements demonstrate this implementation on this identified host
only; they are not universal hardware performance claims.

## Raw-Sample Summary

| Operation | Implementation | Samples | Median (ns) | Mean (ns) | Min (ns) | Max (ns) | Checksum |
|---|---|---:|---:|---:|---:|---:|---:|
| crazy | scalar | 15 | 77456700 | 78035680 | 77213300 | 81112100 | 18595868544 |
| crazy | table | 15 | 7423600 | 7481373 | 7331400 | 7846600 | 18595868544 |
| rotate | scalar | 15 | 15260300 | 15282313 | 15134600 | 15566700 | 223150422528 |
| rotate | table | 15 | 10141700 | 10151460 | 10033300 | 10354700 | 223150422528 |
