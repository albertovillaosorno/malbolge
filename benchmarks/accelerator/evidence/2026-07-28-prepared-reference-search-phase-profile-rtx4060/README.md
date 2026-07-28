# Prepared CPU-reference search phase profile

This directory retains post-preparation search phases after exact CPU-reference
packed equality replaced prepared broadword validation. The workload, seed, budget,
selector, membership index, CPU table, CUDA session, and trusted verifier are
unchanged.

The run used clean source commit
`a5c85767bf8038cc27e281144220094be06630de`, one warmup, and 15 retained fixed-order
profiles per backend with no outlier removal.

## Protocol

- benchmark record: `benchmark.toml`
- experiment run: `experiment.toml`
- raw samples: `raw.csv`
- structured output: `phases.json`
- `phases.json` SHA-256: `7206a8f0f90c32e5e2fd56cb244dc6a997816b838354386456e1910054c25936`
- `raw.csv` SHA-256: `283c2c44c42e9c7d38fcbe87a9acfcc85a8e38ab989671acb3b7fd28590ff30b`

## Environment

- host: Microsoft Windows 10.0.26200 x86-64
- Python: 3.14.6, repository-pinned installation
- CUDA: 13.3 Update 1, repository-pinned toolkit
- NVIDIA driver: 610.47
- device: NVIDIA GeForce RTX 4060 (`sm_89`, 8,188 MiB)

## Proof identity

- ordinary/prepared validators: `u32le-broadword-domain-v1` /
  `cpu-reference-packed-equality-v1`
- prepared reference words: 59049
- CPU evaluations/table entries: 16/59049
- membership/selector: 59049/1
- CUDA builds/evaluations/packed/reuses: 1/16/16/15

## Median comparison

| Backend | Phase | Broadword baseline | CPU-reference equality | Baseline/current |
| --- | --- | ---: | ---: | ---: |
| CPU | Total | 3.067 ms | 2.948 ms | 1.041x |
| CPU | Backend evaluation | 3.039 ms | 2.926 ms | 1.039x |
| CUDA | Total | 0.886 ms | 0.238 ms | 3.729x |
| CUDA | Backend evaluation | 0.860 ms | 0.215 ms | 3.999x |

CUDA total improves **3.729x** and CUDA backend evaluation improves
**3.999x**, so the preregistered hypothesis passes. CPU phases improve about 4%; they
are retained as contextual controls rather than attributed to the CUDA-specific
result representation.

## Interpretation boundary

Phase medians are separate distributions and need not sum. Preparation/reference
creation remains untimed. The remaining CUDA backend phase combines launch/sync,
D-to-H, immutable bytes, contract checks, exact comparison, and result construction.
