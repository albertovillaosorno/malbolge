# Prepared CPU-reference search throughput

This directory retains the full-domain rotate-target search after prepared result
validation changed from broadword domain checking to exact byte equality against
immutable CPU truth computed once during preparation. Ordinary routes retain
`u32le-broadword-domain-v1`; prepared routes require
`cpu-reference-packed-equality-v1` and all 59,049 reference words.

The run used clean source commit
`a5c85767bf8038cc27e281144220094be06630de`, one warmup, and 15 fixed interleaved
samples per route. Preparation, CPU-reference generation, CUDA/NVRTC setup, and the
first resident build are outside retained intervals.

## Protocol

- benchmark record: `benchmark.toml`
- experiment run: `experiment.toml`
- raw samples: `raw.csv`
- structured output: `throughput.json`
- outlier policy: retain all
- center: median
- `throughput.json` SHA-256: `46ec98773588eafeb3ebe9fa8efade86db99c4e7ce3da83a45c61da9da772eac`
- `raw.csv` SHA-256: `138c49e7fb3a2577cc5d07e7a540a4dd7bb06502a8e9b9154b629a7c9e00f79b`

## Environment

- host: Microsoft Windows 10.0.26200 x86-64
- Python: 3.14.6, repository-pinned installation
- CUDA: 13.3 Update 1, repository-pinned toolkit
- NVIDIA driver: 610.47
- device: NVIDIA GeForce RTX 4060 (`sm_89`, 8,188 MiB)

## Proof identity

- ordinary validator: `u32le-broadword-domain-v1`
- prepared validator: `cpu-reference-packed-equality-v1`
- prepared reference words: 59049
- CPU evaluations/table entries: 16/59049
- membership/selector: 59049/1
- CUDA builds/evaluations/packed/reuses: 1/16/16/15

Tests also reject incorrect in-domain output at the first and final word before
proposal selection. Trusted verifier admission remains independent.

## Result

| Route | Broadword baseline | CPU-reference equality | Baseline/current |
| --- | ---: | ---: | ---: |
| CPU ordinary | 213.826 ms | 210.830 ms | 1.014x |
| CPU prepared | 3.179 ms | 3.313 ms | 0.960x |
| CUDA ordinary | 227.033 ms | 223.699 ms | 1.015x |
| CUDA prepared | 1.175 ms | 0.488 ms | 2.407x |

CUDA prepared improves **2.407x**, so the preregistered
hypothesis passes. Same-run CUDA prepared is **6.786x faster** than CPU.
Ordinary controls move about 1.5%; CPU prepared regresses about 4%, so those changes
are retained but not attributed to the CUDA prepared validation change.

## Interpretation boundary

This is amortized repeated-search evidence. The one-time CPU-reference generation is
untimed and costs additional preparation memory. This is not one-shot, stochastic,
compiler, synthesis, or superoptimizer evidence.
