# Prepared primitive-input search throughput

This directory retains the complete 59,049-word rotate-target workload after the
strategy proof began carrying one validated decoded `PrimitiveBatch`. Matching CPU
and CUDA evaluators reuse that hardware-neutral input; ordinary routes still
prepare locally. Every sample preserves exact proposal identity and independent
CPU admission.

The run used a clean detached worktree at source commit
`ed92fd4f6ce8b469b796de059224c9039821ebe8`. Preparation,
CUDA adapter construction, and NVRTC setup are outside prepared-route intervals.
One warmup precedes 15 fixed interleaved CPU ordinary, CPU prepared, CUDA ordinary,
and CUDA prepared samples.

## Protocol

- benchmark record: `benchmark.toml`
- experiment run: `experiment.toml`
- raw samples: `raw.csv`
- structured output: `throughput.json`
- warmup: one execution per route
- retained samples: 15 per route
- ordering: fixed interleaved four-route sequence
- preparation timed: no for prepared routes
- outlier policy: retain all
- center: median
- dispersion/uncertainty: observed minimum-to-maximum range
- `throughput.json` SHA-256: `85d2f2f341235d2308e0b70cec597bfa0d337bda571d4a86df73cb6e6b706c15`
- `raw.csv` SHA-256: `b90c828f2444542b81204061d271b10434bf97cc8c926c8b476b8aac5b38374f`

## Environment

- host: Microsoft Windows 10.0.26200 x86-64
- Python: 3.14.6, repository-pinned installation
- CUDA: 13.3 Update 1, repository-pinned toolkit
- NVIDIA driver: 610.47
- device: NVIDIA GeForce RTX 4060 (`sm_89`, 8,188 MiB)

## Result

| Route | Packed baseline | Prepared-input | Baseline/current |
| --- | ---: | ---: | ---: |
| CPU ordinary | 211.693 ms | 225.721 ms | 0.938x |
| CPU prepared | 77.308 ms | 43.129 ms | 1.792x |
| CUDA ordinary | 230.144 ms | 238.731 ms | 0.964x |
| CUDA prepared | 91.199 ms | 57.296 ms | 1.592x |

Prepared input improves the CPU prepared median **1.792x** and
the CUDA prepared median **1.592x**, so the preregistered
prepared-route hypothesis passes. Within this implementation, prepared execution
is **5.234x** faster than
ordinary CPU and **4.167x**
faster than ordinary CUDA.

Ordinary medians regress: CPU is 6.6% slower and CUDA is 3.7% slower. Those
routes construct the explicit primitive proof locally and are retained as negative
one-shot evidence. Prepared CUDA remains about **32.8% slower** than prepared CPU.

## Interpretation boundary

The improvement is amortized. It applies when immutable candidate input is reused;
one-shot callers still pay validation and decode. The result does not establish a
CUDA advantage, resident device input, stochastic search, compiler throughput, or
superoptimizer performance.
