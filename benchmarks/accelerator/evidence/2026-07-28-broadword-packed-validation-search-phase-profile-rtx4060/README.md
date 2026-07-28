# Broadword packed-domain validation phase profile

This directory retains prepared-search phases after packed u32le domain validation
moved to repeated broadword masks. Exact capability/count checks, immutable bytes,
CPU-table identity, proposal admission, and CUDA resident proofs remain active.

The run used clean source commit
`8c6150a982f21308d05a0367437df4b07fec7497`, one warmup, and 15 retained fixed-order
profiles per backend. Mask construction occurs during the untimed warmup.

## Protocol

- benchmark record: `benchmark.toml`
- experiment run: `experiment.toml`
- raw samples: `raw.csv`
- structured output: `phases.json`
- outlier policy: retain all
- center: median
- `phases.json` SHA-256: `dc5a210351af40682a22a6ce74af67e512407e1167b766870079398589726780`
- `raw.csv` SHA-256: `4d7343f2bad1cb93a37d78b337869e3305dbeeaa979823d46f3f65caef1ff637`

## Environment

- host: Microsoft Windows 10.0.26200 x86-64
- Python: 3.14.6, repository-pinned installation
- CUDA: 13.3 Update 1, repository-pinned toolkit
- NVIDIA driver: 610.47
- device: NVIDIA GeForce RTX 4060 (`sm_89`, 8,188 MiB)

## Proof identity

Validator `u32le-broadword-domain-v1` ran with CPU evaluations/table entries
16/59,049, membership/selector 59,049/1, and CUDA
builds/evaluations/packed/reuses 1/16/16/15.

## Median comparison

| Backend | Phase | Scalar packed baseline | Broadword validation | Baseline/current |
| --- | --- | ---: | ---: | ---: |
| CPU | Total | 2.915 ms | 3.067 ms | 0.950x |
| CPU | Backend evaluation | 2.892 ms | 3.039 ms | 0.952x |
| CPU | Proposal selection | 9.900 us | 13.200 us | 0.750x |
| CUDA | Total | 1.824 ms | 0.886 ms | 2.057x |
| CUDA | Backend evaluation | 1.802 ms | 0.860 ms | 2.095x |
| CUDA | Proposal selection | 9.300 us | 10.800 us | 0.861x |

CUDA backend evaluation improves **2.095x** and CUDA total improves **2.057x**.
Median named coverage remains 99.8% CPU and 99.2% CUDA,
so the preregistered CUDA hypothesis passes. CPU phase regressions are retained as
controls and are not attributed to this CUDA-targeted validation change.

## Interpretation boundary

Phase medians are separate distributions and need not sum. Remaining CUDA backend
cost combines kernel launch/synchronization, D-to-H transfer, immutable byte copy,
and broadword validation; another measured decomposition is required before further
optimization. This is not one-shot or compiler/synthesis evidence.
