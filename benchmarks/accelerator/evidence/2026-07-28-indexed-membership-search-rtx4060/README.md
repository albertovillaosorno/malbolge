# Indexed prepared-membership search throughput

This directory retains the complete 59,049-word rotate-target workload after
`PreparedEvaluatedSearch` began storing one immutable exact membership index.
Prepared CPU and CUDA proposal checks reuse that index; ordinary routes retain the
one-shot dictionary path. Every sample preserves exact proposal identity and
independent CPU admission.

The run used a clean detached worktree at source commit
`f581c40dc96c53584780151f5ea7e57347cc6f13`. One warmup precedes 15 fixed interleaved CPU ordinary, CPU prepared,
CUDA ordinary, and CUDA prepared samples. Preparation, index construction, CUDA
adapter construction, NVRTC, and the first resident-session build are outside the
retained prepared intervals.

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
- `throughput.json` SHA-256: `dee21fcd236152c8ffa802c0685ef78f5c7cc5f58731519f600b95db632d6638`
- `raw.csv` SHA-256: `dc0e4204b81a7b7c7b274afdc1839f0e1136f32a1c9ba718773382c408e2eef6`

## Environment

- host: Microsoft Windows 10.0.26200 x86-64
- Python: 3.14.6, repository-pinned installation
- CUDA: 13.3 Update 1, repository-pinned toolkit
- NVIDIA driver: 610.47
- device: NVIDIA GeForce RTX 4060 (`sm_89`, 8,188 MiB)

## Prepared-proof identity

The benchmark failed closed unless it observed:

- membership index entries: 59049
- CUDA session builds: 1
- CUDA session evaluations: 16
- CUDA session reuses: 15
- resident operation: `rotate`
- resident words: 59049

## Result

| Route | Resident baseline | Indexed membership | Baseline/current |
| --- | ---: | ---: | ---: |
| CPU ordinary | 258.949 ms | 216.529 ms | 1.196x |
| CPU prepared | 46.232 ms | 26.797 ms | 1.725x |
| CUDA ordinary | 279.882 ms | 229.386 ms | 1.220x |
| CUDA prepared | 34.132 ms | 17.970 ms | 1.899x |

Prepared membership improves the CPU prepared median **1.725x**
and the CUDA prepared median **1.899x**, so the preregistered
prepared-route hypothesis passes. CUDA prepared is **1.491x faster** than
same-run CPU prepared.

Ordinary controls also improve by 1.196x CPU and
1.220x CUDA even though they do not use the prepared index.
Those changes bound cross-run attribution: the phase sibling is the direct evidence
for membership-validation reduction.

## Interpretation boundary

This is amortized repeated-search evidence after one untimed index/session build.
It does not measure one-shot latency or index-construction cost. The CUDA advantage
applies only to this exact prepared full-domain rotate workload on this RTX 4060.
It is not stochastic search, compiler throughput, synthesis, or superoptimization.
