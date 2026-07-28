# Direct prepared rotate-selection phase profile

This directory retains post-preparation phase attribution after the rotate strategy
began validating packed evidence only at prepared preimage positions. Exact proposal
identity, full membership validation, resident CUDA identity, and independent CPU
admission remain in the verified path.

The run used a clean detached worktree at source commit
`e36d33f6042842932ba41f0be11850e615457937`. One warmup establishes prepared
selector/index/session state before 15 fixed interleaved CPU-then-CUDA profiles.
All samples and outliers are retained.

## Protocol

- benchmark record: `benchmark.toml`
- experiment run: `experiment.toml`
- raw samples: `raw.csv`
- structured output: `phases.json`
- retained profiles: 15 per backend
- outlier policy: retain all
- center: median
- dispersion/uncertainty: observed minimum-to-maximum range
- `phases.json` SHA-256: `de80b2ddde36455e2dc011753694e4772317cdb0eba30b110bc0d30d71b843db`
- `raw.csv` SHA-256: `22a8c2c08059010b3cff1aa0fa822bc98bbeb18341496ac0be9a7ed2b8187be1`

## Environment

- host: Microsoft Windows 10.0.26200 x86-64
- Python: 3.14.6, repository-pinned installation
- CUDA: 13.3 Update 1, repository-pinned toolkit
- NVIDIA driver: 610.47
- device: NVIDIA GeForce RTX 4060 (`sm_89`, 8,188 MiB)

## Prepared-proof identity

The profile failed closed unless it observed 59,049 membership entries, one
selector position, one CUDA session build, 16 evaluations, 15 reuses, `rotate`, and
59,049 resident words.

## Median phase comparison

| Backend | Phase | Indexed baseline | Direct selection | Baseline/current |
| --- | --- | ---: | ---: | ---: |
| CPU | Total | 26.611 ms | 14.413 ms | 1.846x |
| CPU | Backend evaluation | 14.875 ms | 14.387 ms | 1.034x |
| CPU | Proposal selection | 11.801 ms | 13.200 us | 894.008x |
| CUDA | Total | 17.161 ms | 5.267 ms | 3.258x |
| CUDA | Backend evaluation | 5.421 ms | 5.239 ms | 1.035x |
| CUDA | Proposal selection | 11.761 ms | 12.400 us | 948.452x |

Proposal selection improves **894.008x on CPU** and **948.452x on CUDA**.
Samplewise median named-phase coverage remains 100.0% CPU and 99.9% CUDA, so the
preregistered selection/coverage hypothesis passes.

Backend medians improve only 1.034x CPU and 1.035x CUDA, while ordinary controls
improve
about one percent. The near-thousand-fold direct phase reduction is therefore the
primary evidence for prepared exact-position selection.

## Interpretation boundary

Phase medians come from separate distributions; component medians need not sum to
the total median. Selector-state construction is outside retained intervals. The
remaining prepared path is dominated by primitive backend evaluation, not proposal
selection. This is not one-shot, stochastic, compiler, synthesis, or superoptimizer
evidence.
