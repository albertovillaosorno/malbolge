# Prepared primitive-input phase profile

This directory retains post-preparation phase attribution after the strategy proof
began storing one validated decoded `PrimitiveBatch`. The complete 59,049-word
workload, packed evidence representation, proposal identity, and independent CPU
admission remain unchanged.

The run used a clean detached worktree at source commit
`ed92fd4f6ce8b469b796de059224c9039821ebe8`. Preparation,
CUDA adapter construction, and NVRTC setup are outside retained intervals. One
warmup precedes 15 fixed interleaved CPU-then-CUDA profiles.

## Protocol

- benchmark record: `benchmark.toml`
- experiment run: `experiment.toml`
- raw samples: `raw.csv`
- structured output: `phases.json`
- retained profiles: 15 per backend
- preparation timed: no
- outlier policy: retain all
- center: median
- dispersion/uncertainty: observed minimum-to-maximum range
- `phases.json` SHA-256: `1614b53885c39db3afd2845dc8026aa84c7b712304e1efe8399c3ec979b6ae2e`
- `raw.csv` SHA-256: `5ca83268c414ed9bfc2d90c25a9830919ba72dc88484626649c49af6cef112b3`

## Environment

- host: Microsoft Windows 10.0.26200 x86-64
- Python: 3.14.6, repository-pinned installation
- CUDA: 13.3 Update 1, repository-pinned toolkit
- NVIDIA driver: 610.47
- device: NVIDIA GeForce RTX 4060 (`sm_89`, 8,188 MiB)

## Median phase comparison

| Backend | Phase | Packed baseline | Prepared input | Baseline/current |
| --- | --- | ---: | ---: | ---: |
| CPU | Total | 76.347 ms | 42.428 ms | 1.799x |
| CPU | Backend evaluation | 53.907 ms | 19.246 ms | 2.801x |
| CPU | Proposal selection | 22.502 ms | 23.076 ms | 0.975x |
| CUDA | Total | 89.624 ms | 55.300 ms | 1.621x |
| CUDA | Backend evaluation | 67.202 ms | 32.264 ms | 2.083x |
| CUDA | Proposal selection | 22.288 ms | 22.913 ms | 0.973x |

Backend evaluation falls **2.801x on CPU** and
**2.083x on CUDA**. Samplewise median named
coverage remains 100.0% and 100.0%, so the
preregistered phase hypothesis passes. Proposal-selection medians are essentially
unchanged and are retained rather than attributed to input preparation.

## Interpretation boundary

The remaining prepared backend phase now consists primarily of primitive execution,
packed output creation, and capability/result checks. CUDA still performs host
buffer construction, allocation, H-to-D transfer, kernel execution, D-to-H transfer,
and release on every prepared call. A resident primitive session is the next
measured CUDA boundary; CPU primitive arithmetic remains the CPU boundary.
