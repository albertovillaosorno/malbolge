# Resident primitive-input search throughput

This directory retains the complete 59,049-word rotate-target workload after CUDA
prepared execution began retaining one proof-bound device input/output allocation
and host output buffer. Ordinary CUDA remains one-shot. Every sample preserves exact
proposal identity and independent CPU admission.

The run used a clean detached worktree at source commit
`877cce02fd3f3868d6a4e320d9cb96591e64a630`. One warmup precedes 15
fixed interleaved CPU ordinary, CPU prepared, CUDA ordinary, and CUDA prepared
samples. Preparation, adapter construction, NVRTC,
and the first resident-session build are outside retained prepared intervals.

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
- `throughput.json` SHA-256: `cd7358855718b8c35ec25e02f8ac4cdf1a2fda330fed72973ae08e13044a5f35`
- `raw.csv` SHA-256: `dc1a934bcbb4ac981df914a8ba59912ceda6b29ed39fbbefabb664cd57f4f455`

## Environment

- host: Microsoft Windows 10.0.26200 x86-64
- Python: 3.14.6, repository-pinned installation
- CUDA: 13.3 Update 1, repository-pinned toolkit
- NVIDIA driver: 610.47
- device: NVIDIA GeForce RTX 4060 (`sm_89`, 8,188 MiB)

## Resident-session proof

The benchmark failed closed unless the CUDA adapter reported exactly:

- builds: 1
- evaluations: 16
- reuses: 15
- resident operation: `rotate`
- resident words: 59049

## Result

| Route | Prepared-input baseline | Resident implementation | Baseline/current |
| --- | ---: | ---: | ---: |
| CPU ordinary | 225.721 ms | 258.949 ms | 0.872x |
| CPU prepared | 43.129 ms | 46.232 ms | 0.933x |
| CUDA ordinary | 238.731 ms | 279.882 ms | 0.853x |
| CUDA prepared | 57.296 ms | 34.132 ms | 1.679x |

CUDA prepared improves **1.679x** versus the retained
prepared-input baseline and is **1.355x faster** than same-run CPU prepared.
The preregistered resident-session hypothesis therefore passes.

The control routes are slower than the prior run: CPU ordinary/prepared change by
14.7%/7.2%, and CUDA ordinary changes by 17.2%.
Those paths do not use the resident prepared session. Their regressions and wider
ranges are retained as run-context/noise evidence, not attributed to residence.

## Interpretation boundary

This is amortized repeated-search evidence after one untimed session build. It does
not measure one-shot CUDA latency. The result establishes a CUDA advantage only for
this exact full-domain prepared rotate workload on this RTX 4060. It is not
stochastic search, compiler throughput, synthesis, or superoptimizer evidence.
