# Multiposition crazy-target performance matrix

This bundle retains the exact full-domain `classic-crazy-target-search-v1`
performance matrix from clean source commit `a225195d394020cdd354828df33966d61a1e5059`. The workload contains all
59,049 classic words, fixed accumulator zero, target 29,524, and exactly 1,024
algebraic preimages derived from the shared `CRAZY_TRIT_TABLE`.

## Protocol and identity

- benchmark record: `benchmark.toml`
- experiment run: `experiment.toml`
- structured output: `throughput.json`
- raw chronological samples: `raw.csv`
- source commit: `a225195d394020cdd354828df33966d61a1e5059`
- one warmup per route; 15 retained samples per route
- cyclic first-route rotation over five routes; all samples retained
- prepared construction and adapter/NVRTC setup are untimed
- CUDA ticket batch/selector preparation, one-shot allocation, launch, wait,
  exact validation, and cleanup are timed
- full membership: 59,049
- projected reference/selection count: 1,024/1,024
- CPU prepared builds/evaluations/reuses/resident: 1/16/15/1,024
- CUDA prepared builds/evaluations/packed/reuses/resident: 1/16/16/15/1,024
- search ticket: `classic-crazy-target-search-submission-v1`
- `throughput.json` SHA-256: `8612e5fc848d7a98242ade2bf26c3bb5a21c91866454372b9414658f4729d04f`
- `raw.csv` SHA-256: `0b053e89b7f0d69175dea4568b7f74e43a0a2b6450869bf4a39960942eea4ad7`

## Environment

- host: Microsoft Windows 11 Pro 10.0.26200 x86-64
- Python: 3.14.6, repository-pinned installation
- CUDA toolkit: 13.3.1 (`nvcc` 13.3.73)
- NVIDIA driver: 610.47
- device: NVIDIA GeForce RTX 4060 (`sm_89`, 8,188 MiB)

## Results

| Route | Median | Min | Max | Population SD |
| --- | ---: | ---: | ---: | ---: |
| CPU ordinary | 368.3588 ms | 366.2973 ms | 408.1793 ms | 12.5578 ms |
| CPU prepared | 22.4264 ms | 22.2029 ms | 27.7982 ms | 1.3482 ms |
| CUDA ordinary | 235.8490 ms | 232.6327 ms | 245.5543 ms | 3.8594 ms |
| CUDA prepared | 20.3304 ms | 19.5479 ms | 21.7950 ms | 0.5415 ms |
| CUDA ticket one-shot | 185.7629 ms | 183.0156 ms | 201.6606 ms | 4.4239 ms |

- CPU prepared over ordinary: **16.425x**, 15/15 paired wins, 346.0322 ms paired-median saving.
- CUDA prepared over ordinary: **11.601x**, 15/15 wins, 215.3769 ms saving.
- CUDA prepared over CPU prepared: **1.103x** in the same run.
- CUDA ticket over CUDA ordinary: **1.270x**, 15/15 wins, 49.8834 ms saving.
- CUDA prepared over the one-shot ticket: **9.137x**.

The preregistered prepared-route hypothesis passes for both CPU and CUDA. The
one-shot neutral ticket also improves over ordinary CUDA for every retained pair,
but remains much slower than amortized prepared CUDA because it intentionally
includes complete request/batch/selector preparation, one-shot buffers, exact CPU
reference validation, and cleanup on every submission.

## Interpretation boundary

This evidence supports exact projection and explicit ticket-lifetime performance
for one deterministic full-domain workload on one RTX 4060. It is not compiler,
synthesis, stochastic-search, cross-device, kernel-overlap, or independent-stream
evidence. Prepared timings exclude one-time preparation and therefore answer an
amortized reuse question; ticket timings answer a one-shot submission question.
