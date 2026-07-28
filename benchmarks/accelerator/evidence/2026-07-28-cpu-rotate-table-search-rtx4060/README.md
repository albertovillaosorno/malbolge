# Prepared CPU rotate-table throughput

This directory retains the complete 59,049-word rotate-target workload after the
prepared CPU adapter began using one full-domain lookup table generated from the
ordinary scalar formula. Ordinary CPU execution remains scalar. An exhaustive test
compares every classic-domain result before this benchmark evidence is considered.

The run used a clean detached worktree at source commit
`50504ee29d55d26bc79fb2eec3ebad255e44c261`. One warmup precedes 15 fixed interleaved CPU ordinary, CPU prepared,
CUDA ordinary, and CUDA prepared samples. Table generation, search preparation,
CUDA adapter setup, NVRTC, and the first resident CUDA build are outside retained
prepared intervals.

## Protocol

- benchmark record: `benchmark.toml`
- experiment run: `experiment.toml`
- raw samples: `raw.csv`
- structured output: `throughput.json`
- warmup: one execution per route
- retained samples: 15 per route
- ordering: fixed interleaved four-route sequence
- outlier policy: retain all
- center: median
- dispersion/uncertainty: observed minimum-to-maximum range
- `throughput.json` SHA-256: `95eb8a1dcce933c9a64337f6673adda4f6abfd19bbe75db3c5c018252f2b6050`
- `raw.csv` SHA-256: `2a5daf19cd4191e7b5d7de7b9ee010ab0b41307d04c4e1ad937d7b3ecf4d5b44`

## Environment

- host: Microsoft Windows 10.0.26200 x86-64
- Python: 3.14.6, repository-pinned installation
- CUDA: 13.3 Update 1, repository-pinned toolkit
- NVIDIA driver: 610.47
- device: NVIDIA GeForce RTX 4060 (`sm_89`, 8,188 MiB)

## Prepared-proof identity

The benchmark failed closed unless it observed:

- CPU prepared evaluations/table entries: 16/59049
- membership index entries: 59049
- exact prepared selector positions: 1
- CUDA session builds/evaluations/reuses: 1/16/15
- resident CUDA operation/words: `rotate`/59049

## Result

| Route | Extrema baseline | CPU rotate table | Baseline/current |
| --- | ---: | ---: | ---: |
| CPU ordinary | 213.488 ms | 213.563 ms | 1.000x |
| CPU prepared | 14.058 ms | 3.313 ms | 4.243x |
| CUDA ordinary | 227.646 ms | 230.899 ms | 0.986x |
| CUDA prepared | 4.929 ms | 4.769 ms | 1.033x |

CPU prepared improves **4.243x**, so the preregistered hypothesis passes. Same-run
CPU prepared is **1.440x faster** than CUDA prepared. CPU ordinary is effectively
unchanged (0.9996x),
while CUDA routes change only modestly, supporting attribution to the prepared CPU
lookup table.

## Interpretation boundary

This is amortized repeated-search evidence. It excludes one-time table generation
and does not claim one-shot improvement. The table is derived from and exhaustively
checked against the ordinary scalar formula; it is not a second semantic authority.
This is not stochastic, compiler, synthesis, or superoptimizer evidence.
