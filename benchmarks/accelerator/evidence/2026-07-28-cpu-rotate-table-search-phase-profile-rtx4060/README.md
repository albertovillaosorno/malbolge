# Prepared CPU rotate-table phase profile

This directory retains prepared-search phase attribution after the CPU adapter began
using a scalar-derived full-domain rotate table. Ordinary CPU remains scalar, and an
exhaustive test compares all 59,049 classic-domain outputs.

The run used a clean detached worktree at source commit
`50504ee29d55d26bc79fb2eec3ebad255e44c261`. One warmup establishes table/index/selector/session state before 15
fixed interleaved CPU-then-CUDA profiles. All samples and outliers are retained.

## Protocol

- benchmark record: `benchmark.toml`
- experiment run: `experiment.toml`
- raw samples: `raw.csv`
- structured output: `phases.json`
- retained profiles: 15 per backend
- outlier policy: retain all
- center: median
- dispersion/uncertainty: observed minimum-to-maximum range
- `phases.json` SHA-256: `020628c8533addf48059337b0ca8e826c6cd16190c4b155f7a39cb96284eb5ec`
- `raw.csv` SHA-256: `cf161a606e0d49ada830e645d2af3a86ca6b5d69c648df46db0b8496b792a774`

## Environment

- host: Microsoft Windows 10.0.26200 x86-64
- Python: 3.14.6, repository-pinned installation
- CUDA: 13.3 Update 1, repository-pinned toolkit
- NVIDIA driver: 610.47
- device: NVIDIA GeForce RTX 4060 (`sm_89`, 8,188 MiB)

## Prepared-proof identity

The profile failed closed unless it observed CPU evaluations/table entries
16/59,049, membership 59,049, selector count 1, CUDA builds/evaluations/reuses
1/16/15, and `rotate`/59,049 resident words.

## Median phase comparison

| Backend | Phase | Extrema baseline | CPU rotate table | Baseline/current |
| --- | --- | ---: | ---: | ---: |
| CPU | Total | 13.223 ms | 2.928 ms | 4.516x |
| CPU | Backend evaluation | 13.190 ms | 2.906 ms | 4.540x |
| CPU | Proposal selection | 12.700 us | 10.400 us | 1.221x |
| CUDA | Total | 3.967 ms | 3.896 ms | 1.018x |
| CUDA | Backend evaluation | 3.940 ms | 3.868 ms | 1.018x |
| CUDA | Proposal selection | 11.800 us | 11.700 us | 1.009x |

CPU backend evaluation improves **4.540x** and CPU total improves **4.516x**.
Samplewise median named-phase coverage remains 99.8% CPU and 99.8% CUDA, so the
preregistered CPU hypothesis passes. CUDA
phases change only about two percent and remain contextual controls.

## Interpretation boundary

Table construction occurs outside retained intervals. Phase medians come from
separate distributions and need not sum to total median. The remaining CPU backend
cost is result validation/packing; the remaining CUDA cost is host
materialization/packing rather than kernel execution. This is not one-shot,
stochastic, compiler, synthesis, or superoptimizer evidence.
