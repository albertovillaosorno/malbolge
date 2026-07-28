# Resident primitive-input phase profile

This directory retains post-preparation phase attribution for the same full-domain
rotate workload after CUDA input/output became proof-bound and resident. Exact
proposal identity and independent CPU admission remain unchanged.

The run used a clean detached worktree at source commit
`877cce02fd3f3868d6a4e320d9cb96591e64a630`. One warmup establishes the
resident session before 15 fixed interleaved CPU-then-CUDA profiles. All samples
and outliers are retained.

## Protocol

- benchmark record: `benchmark.toml`
- experiment run: `experiment.toml`
- raw samples: `raw.csv`
- structured output: `phases.json`
- retained profiles: 15 per backend
- outlier policy: retain all
- center: median
- dispersion/uncertainty: observed minimum-to-maximum range
- `phases.json` SHA-256: `a67d4f26331f08fdba7c78d1505c97ac97f1a7d535f9153fe68e600611b52359`
- `raw.csv` SHA-256: `065552b7307a3688a70afae9391557a94bd4162cd69801b7dd50597e262b8e9d`

## Environment

- host: Microsoft Windows 10.0.26200 x86-64
- Python: 3.14.6, repository-pinned installation
- CUDA: 13.3 Update 1, repository-pinned toolkit
- NVIDIA driver: 610.47
- device: NVIDIA GeForce RTX 4060 (`sm_89`, 8,188 MiB)

## Resident-session proof

The profile failed closed unless it observed one build, 16 evaluations, 15 reuses,
`rotate`, and 59049 resident words.

## Median phase comparison

| Backend | Phase | Prepared-input baseline | Resident implementation | Baseline/current |
| --- | --- | ---: | ---: | ---: |
| CPU | Total | 42.428 ms | 63.249 ms | 0.671x |
| CPU | Backend evaluation | 19.246 ms | 23.153 ms | 0.831x |
| CPU | Proposal selection | 23.076 ms | 41.529 ms | 0.556x |
| CUDA | Total | 55.300 ms | 55.910 ms | 0.989x |
| CUDA | Backend evaluation | 32.264 ms | 9.922 ms | 3.252x |
| CUDA | Proposal selection | 22.913 ms | 46.331 ms | 0.495x |

CUDA backend evaluation improves **3.252x**. Samplewise median named-phase
coverage is 100.0% CPU and 100.0% CUDA, so the preregistered backend/coverage
hypothesis passes.

The complete CUDA profile does **not** improve: total changes from 55.300 to
55.910 ms because proposal selection rises from 22.913 to 46.331 ms in this noisy
run.
CPU phases rise similarly. These negative/context observations are retained. The
next evidence-driven boundary is proposal selection and membership validation, not
further input residency.

## Interpretation boundary

Phase medians come from separate distributions; component medians need not sum to
the total median. This evidence supports a resident CUDA backend reduction, not a
complete phase-profile speedup. The throughput sibling is the end-to-end prepared
search result for this commit.
