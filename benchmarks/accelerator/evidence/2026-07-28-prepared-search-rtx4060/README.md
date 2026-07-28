# Prepared full-domain search evidence

This directory retains a deterministic comparison of ordinary and prepared
`classic-rotate-target-search-v1` execution on the exact CPU reference and live
CUDA backend. The workload contains every classic word from 0 through 59,048,
uses seed 17, target 19,683, and an evaluation budget of 59,049.

The run used a clean detached worktree at source commit
`1401dfd22a806cebc18f28c2d94de216de1309a2`. One CPU adapter prepared immutable validated request/batch state before
measurement. The same strategy-bound proof was reused by both CPU and CUDA.
Preparation, adapter construction, and NVRTC/module setup are outside timed
intervals. One warmup preceded 15 fixed interleaved samples in this order: CPU
ordinary, CPU prepared, CUDA ordinary, CUDA prepared. Every sample produced the
same proposal and passed independent CPU admission.

## Protocol

- benchmark record: `benchmark.toml`
- experiment run: `experiment.toml`
- raw samples: `raw.csv`
- structured output: `throughput.json`
- warmup: one execution per route
- retained samples: 15 per route
- ordering: fixed interleaved four-route sequence
- preparation timed: no
- outlier policy: retain all
- center: median
- dispersion/uncertainty: observed minimum-to-maximum range
- `throughput.json` SHA-256: `aadf3d51a65c337ff795076f744beaa333e231af83a46225c99cce51aaa9c68b`
- `raw.csv` SHA-256: `37137ca922adf63bec0113dc99dea590bfc73b8ab4a3e0396fe2c2e284ef9d0c`

## Environment

- host: Microsoft Windows 10.0.26200 x86-64
- Python: 3.14.6, repository-pinned installation
- CUDA: 13.3 Update 1, repository-pinned toolkit
- NVIDIA driver: 610.47
- device: NVIDIA GeForce RTX 4060 (`sm_89`, 8,188 MiB)

## Result

| Route | Median | Minimum | Maximum | Population standard deviation |
| --- | ---: | ---: | ---: | ---: |
| CPU ordinary | 293.564 ms | 281.308 ms | 311.010 ms | 8.158 ms |
| CPU prepared | 148.590 ms | 146.621 ms | 173.837 ms | 7.166 ms |
| CUDA ordinary | 306.872 ms | 296.285 ms | 324.317 ms | 7.207 ms |
| CUDA prepared | 162.693 ms | 159.387 ms | 174.337 ms | 3.915 ms |

Prepared execution improves same-backend median repeated-search wall time by
**1.976x on CPU** and
**1.886x on CUDA**. The preregistered
prepared-state hypothesis therefore passes for both backends.

Prepared CUDA remains slower than prepared CPU on this workload. The observed
CPU-prepared/CUDA-prepared ratio is
**0.913x**, meaning CUDA is about
**9.5% slower by median wall time**. Prepared state removes
repeated host construction and validation; it does not by itself establish a CUDA
advantage.

## Interpretation boundary

These are amortized repeated-search measurements. The one-time preparation cost is
outside the timed intervals, so the prepared medians must not be presented as
one-shot search latency. Ordinary routes remain the appropriate baseline when a
request is executed only once or cannot reuse immutable candidate state.

The comparison demonstrates that reusable validated search state addresses the
host-side bottleneck selected by the prior phase profile. It does not measure a
resident GPU corpus, fused device-side selection, stochastic search, Malbolge
program synthesis, compiler throughput, or a superoptimizer.
