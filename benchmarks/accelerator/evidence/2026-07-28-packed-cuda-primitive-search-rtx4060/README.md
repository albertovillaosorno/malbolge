# Validated packed CUDA primitive throughput

This directory retains the complete 59,049-word rotate-target workload after
prepared CUDA began returning immutable canonical u32le bytes directly from the
resident host output buffer. The neutral bridge still validates backend capability,
exact byte count, and every classic-domain word before reusing those bytes as
candidate evidence. Ordinary CUDA and all CPU routes remain tuple-compatible.

The run used a clean detached worktree at source commit
`90b9bbdc3047691f53103fc4927fd7cdbe715f24`. One warmup precedes 15 fixed
interleaved CPU ordinary, CPU prepared, CUDA ordinary, and CUDA prepared samples. Search preparation, CPU table generation,
CUDA adapter setup, NVRTC, and the first resident build are outside retained
prepared intervals.

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
- `throughput.json` SHA-256: `6f1f1f357b52ba029a099f465adb24369b5fca8825302f340f7f33633d0a1acc`
- `raw.csv` SHA-256: `6751d663d7ea733755122439ebbe38cb0ad9966ac6006b7fc71526296c7c795c`

## Environment

- host: Microsoft Windows 10.0.26200 x86-64
- Python: 3.14.6, repository-pinned installation
- CUDA: 13.3 Update 1, repository-pinned toolkit
- NVIDIA driver: 610.47
- device: NVIDIA GeForce RTX 4060 (`sm_89`, 8,188 MiB)

## Prepared-proof identity

The benchmark failed closed unless it observed:

- CPU prepared evaluations/table entries: 16/59049
- membership index entries: 59049
- exact prepared selector positions: 1
- CUDA builds/evaluations/packed/reuses: 1/16/16/15
- resident CUDA operation/words: `rotate`/59049

## Result

| Route | CPU-table baseline | Packed CUDA result | Baseline/current |
| --- | ---: | ---: | ---: |
| CPU ordinary | 213.563 ms | 214.581 ms | 0.995x |
| CPU prepared | 3.313 ms | 3.300 ms | 1.004x |
| CUDA ordinary | 230.899 ms | 231.443 ms | 0.998x |
| CUDA prepared | 4.769 ms | 2.036 ms | 2.343x |

CUDA prepared improves **2.343x**, so the preregistered hypothesis passes. Same-run
CUDA prepared is **1.621x faster** than CPU prepared. CPU prepared changes only
1.004x, and ordinary controls remain effectively flat/slightly slower, supporting attribution to the
prepared CUDA packed-result route.

## Interpretation boundary

This is amortized repeated-search evidence. It excludes one-time setup and does not
claim one-shot improvement. Packed bytes remain untrusted until the neutral bridge
validates immutable representation, capability, count, and every result word. This
is not stochastic, compiler, synthesis, or superoptimizer evidence.
