# Prepared search preparation and crossover evidence

This directory retains the preregistered four-scale measurement of exact prepared
rotate-target search. It includes fresh-process cold preparation, warm-process
preparation after the shared rotate table exists, incremental Python allocation,
ordinary CUDA, fresh resident build plus one exact search, and resident reuse.

The run used clean source commit
`f1e26800c8642e22fa135adb753550b7f780f4c3` on one RTX 4060. Every timing metric
has 15 retained samples; each traced-memory metric has five. No outliers were
removed.
Workload construction, CUDA/NVRTC adapter setup, and trusted result admission are
outside timed intervals. Cold preparation runs in a fresh Python process per sample.

## Protocol

- benchmark record: `benchmark.toml`
- experiment run: `experiment.toml`
- structured output: `crossover.json`
- raw samples: `raw.csv`
- source commit: `source-commit.txt`
- `crossover.json` SHA-256:
  `28edc7fa8c11a4304efc54a34ddd715ea2645cde222da7eb673da1f88e7d2988`
- `raw.csv` SHA-256:
  `0f180d9ddd76c8ecb55be232fd1fca94a53e76ea082677047e34bb5704329c4c`
- aggregate workload SHA-256:
  `4448fd7594a50646c5da2ccea28b239fb80da4b16a005739f33db56ce5aa3777`

## Environment

- host: Microsoft Windows 10.0.26200 x86-64
- Python: 3.14.6, repository-pinned installation
- CUDA: 13.3 Update 1, repository-pinned toolkit
- NVIDIA driver: 610.47
- device: NVIDIA GeForce RTX 4060 (`sm_89`, 8,188 MiB)

## Proof identity

- ordinary validator: `u32le-broadword-domain-v1`
- prepared validator: `cpu-reference-packed-equality-v1`
- strict crossover inequality retained in JSON
- reference and membership counts equal each candidate scale
- selector count is exactly one at every scale
- every fresh session proves builds/evaluations/packed/reuses = 1/1/1/0
- every reuse route proves builds/evaluations/packed/reuses = 1/17/17/16
- every result preserves the exact proposal and independent trusted admission

## Median results

| Candidates | Cold prepare | Warm prepare | Ordinary | Fresh build | Reuse |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 12.198 ms | 0.075 ms | 0.235 ms | 0.747 ms | 0.113 ms |
| 64 | 12.415 ms | 0.278 ms | 0.469 ms | 0.750 ms | 0.121 ms |
| 1,024 | 15.660 ms | 3.363 ms | 3.808 ms | 0.929 ms | 0.131 ms |
| 59,049 | 216.196 ms | 200.568 ms | 222.842 ms | 11.572 ms | 0.407 ms |

| Candidates | Cold crossover | Warm crossover | Retained Python | Peak Python |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 106 | 6 | 0.002 MiB | 0.003 MiB |
| 64 | 38 | 3 | 0.017 MiB | 0.020 MiB |
| 1,024 | 5 | 2 | 0.269 MiB | 0.316 MiB |
| 59,049 | 2 | 1 | 16.063 MiB | 19.040 MiB |

The strict warm crossover sequence is **6, 3, 2, 1** runs; the cold sequence is
**106, 38, 5, 2**. At full domain, warm preparation plus the first resident search
is 212.140 ms versus 222.842 ms ordinary, a 10.703 ms one-shot advantage.
Cold preparation plus first search is 227.767 ms, so the fresh-process path
crosses on its second execution.

## Memory result

The exact full-domain reference is 236,196 bytes. Deterministic reference,
CUDA device input/output, and host output buffers total 944,784 bytes
(0.901 MiB). Incremental traced Python state retains 16,843,645 bytes
(16.063 MiB) and peaks at 19,964,669 bytes (19.040 MiB): 71.312x and
84.526x the reference bytes alone. Full-domain retained allocation is
285.249 bytes per candidate.

## Interpretation boundary

`tracemalloc` covers incremental Python allocations only. It excludes the prebuilt
canonical workload, the process-wide rotate table, CUDA allocations, native ctypes
storage, interpreter/import cost, and adapter/NVRTC setup. The result therefore
supports compacting prepared Python candidate/membership state; it is not total
process RSS or total GPU memory evidence. It is deterministic rotate-target search
evidence, not synthesis, stochastic search, compiler, ROCm, or multi-device evidence.
