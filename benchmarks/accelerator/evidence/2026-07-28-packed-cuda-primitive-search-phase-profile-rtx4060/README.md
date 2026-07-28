# Validated packed CUDA primitive phase profile

This directory retains prepared-search phase attribution after CUDA began exposing
immutable packed u32le output directly from its resident host buffer. The neutral
bridge continues validating capability, exact result count, and every output word
before candidate evidence acceptance.

The run used a clean detached worktree at source commit
`90b9bbdc3047691f53103fc4927fd7cdbe715f24`. One warmup establishes
 table/index/selector/session state before 15 fixed interleaved CPU-then-CUDA
profiles. All samples and outliers are retained.

## Protocol

- benchmark record: `benchmark.toml`
- experiment run: `experiment.toml`
- raw samples: `raw.csv`
- structured output: `phases.json`
- retained profiles: 15 per backend
- outlier policy: retain all
- center: median
- dispersion/uncertainty: observed minimum-to-maximum range
- `phases.json` SHA-256: `cfe7fe41b7c2c26fa8aa81ec739e833a3ad1abf0eff33b2d35ccb73f14abb200`
- `raw.csv` SHA-256: `d7a07d254f968e37797f2cada5ffc7fc9c27844c851cb039fd752637782b051b`

## Environment

- host: Microsoft Windows 10.0.26200 x86-64
- Python: 3.14.6, repository-pinned installation
- CUDA: 13.3 Update 1, repository-pinned toolkit
- NVIDIA driver: 610.47
- device: NVIDIA GeForce RTX 4060 (`sm_89`, 8,188 MiB)

## Prepared-proof identity

The profile failed closed unless it observed CPU evaluations/table entries
16/59,049, membership 59,049, selector count 1, CUDA
builds/evaluations/packed/reuses 1/16/16/15, and `rotate`/59,049 resident words.

## Median phase comparison

| Backend | Phase | CPU-table baseline | Packed CUDA result | Baseline/current |
| --- | --- | ---: | ---: | ---: |
| CPU | Total | 2.928 ms | 2.915 ms | 1.005x |
| CPU | Backend evaluation | 2.906 ms | 2.892 ms | 1.005x |
| CPU | Proposal selection | 10.400 us | 9.900 us | 1.051x |
| CUDA | Total | 3.896 ms | 1.824 ms | 2.136x |
| CUDA | Backend evaluation | 3.868 ms | 1.802 ms | 2.147x |
| CUDA | Proposal selection | 11.700 us | 9.300 us | 1.258x |

CUDA backend evaluation improves **2.147x** and CUDA total improves **2.136x**.
Samplewise median named-phase coverage remains 99.8% CPU and 99.7% CUDA, so the
preregistered CUDA hypothesis passes. CPU
phases change by about half a percent and remain contextual controls.

## Interpretation boundary

Phase medians come from separate distributions and need not sum to total median.
The remaining prepared CUDA cost is dominated by packed-domain validation rather
than tuple construction or repacking. This evidence does not claim one-shot,
stochastic, compiler, synthesis, or superoptimizer performance.
