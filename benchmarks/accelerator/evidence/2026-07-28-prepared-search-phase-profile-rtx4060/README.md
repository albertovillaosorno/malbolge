# Prepared full-domain search phase profile

This directory retains post-preparation phase attribution for the complete
59,049-word `classic-rotate-target-search-v1` workload on the exact CPU reference
and live CUDA backend. One CPU adapter prepares immutable validated request/batch
state before measurement; the same strategy-bound proof is consumed by both
backends. Every profile produces the expected proposal and passes independent CPU
admission.

The run used a clean detached worktree at source commit
`e21ffdf42a4fe9d7e5f2200cbf885e6669ccaf96`. Preparation, CUDA adapter construction, and NVRTC/module setup are
outside retained intervals. One warmup preceded 15 fixed interleaved CPU-then-CUDA
profiles. Retained phases are prepared-proof validation, backend evaluation,
proposal selection, result validation, and inclusive total time.

## Protocol

- benchmark record: `benchmark.toml`
- experiment run: `experiment.toml`
- raw samples: `raw.csv`
- structured output: `phases.json`
- warmup: one prepared profile per backend
- retained profiles: 15 per backend
- ordering: fixed interleaved CPU then CUDA
- preparation timed: no
- outlier policy: retain all
- center: median
- dispersion/uncertainty: observed minimum-to-maximum range
- `phases.json` SHA-256: `b2719d105a45267dcd38a9a6ee843eff4eb51c02096c5cf23c79e7ba0661fc02`
- `raw.csv` SHA-256: `1ff6ca6f9f1fdbba949c71da9c97553be3df74261ac1e632935afb129536398f`

## Environment

- host: Microsoft Windows 10.0.26200 x86-64
- Python: 3.14.6, repository-pinned installation
- CUDA: 13.3 Update 1, repository-pinned toolkit
- NVIDIA driver: 610.47
- device: NVIDIA GeForce RTX 4060 (`sm_89`, 8,188 MiB)

## Median phase attribution

| Backend | Total | Backend evaluation | Proposal selection | Proof validation | Result validation | Named coverage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| CPU reference | 156.935 ms | 125.412 ms | 30.796 ms | 0.001800 ms | 0.026 ms | 99.6% |
| CUDA | 170.276 ms | 138.320 ms | 31.912 ms | 0.001900 ms | 0.023 ms | 100.0% |

Named phases explain more than 99.5% of median total time on both backends, and
backend evaluation is the largest phase. It accounts for about
**79.9% of CPU** and **81.2% of CUDA**
median total time. Proposal selection accounts for about
**19.6% of CPU** and **18.7% of CUDA**.
The preregistered phase-attribution hypothesis therefore passes.

## Interpretation

Prepared proof validation and final result validation are negligible. After batch
construction is amortized, the dominant cost is candidate-evaluation transport and
materialization, followed by host proposal selection. The next evidence-driven
optimization boundary is therefore the candidate-evaluation result representation
and transfer path; a fused or resident evaluation/selection route remains a later
option if exact equivalence is retained.

These diagnostic totals must not replace the ordinary-versus-prepared throughput
record under `../2026-07-28-prepared-search-rtx4060/`. Instrumentation and run noise
differ. This evidence identifies where prepared time remains; it does not establish
a new CPU/CUDA speedup result or include the one-time preparation cost.
