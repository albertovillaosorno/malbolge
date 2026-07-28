# Indexed prepared-membership phase profile

This directory retains post-preparation phase attribution for the full-domain
rotate workload after exact proposal membership became an immutable prepared index.
The packed evidence scan, proposal construction, exact payload membership, and
independent CPU admission remain in the measured/verified path.

The run used a clean detached worktree at source commit
`f581c40dc96c53584780151f5ea7e57347cc6f13`. One warmup establishes the index and resident CUDA session before 15
fixed interleaved CPU-then-CUDA profiles. All samples and outliers are retained.

## Protocol

- benchmark record: `benchmark.toml`
- experiment run: `experiment.toml`
- raw samples: `raw.csv`
- structured output: `phases.json`
- retained profiles: 15 per backend
- outlier policy: retain all
- center: median
- dispersion/uncertainty: observed minimum-to-maximum range
- `phases.json` SHA-256: `0bc685ada3c8ef848c09a0079d742dd212c7a55afecd3bcd42949256161b3020`
- `raw.csv` SHA-256: `b2224dc22f74997ef6b478ed4b301efbaf89a883f43c69832996858e2c23e079`

## Environment

- host: Microsoft Windows 10.0.26200 x86-64
- Python: 3.14.6, repository-pinned installation
- CUDA: 13.3 Update 1, repository-pinned toolkit
- NVIDIA driver: 610.47
- device: NVIDIA GeForce RTX 4060 (`sm_89`, 8,188 MiB)

## Prepared-proof identity

The profile failed closed unless it observed 59049 indexed members,
one CUDA session build, 16 evaluations, 15 reuses, `rotate`,
and 59049 resident words.

## Median phase comparison

| Backend | Phase | Resident baseline | Indexed membership | Baseline/current |
| --- | --- | ---: | ---: | ---: |
| CPU | Total | 63.249 ms | 26.611 ms | 2.377x |
| CPU | Backend evaluation | 23.153 ms | 14.875 ms | 1.557x |
| CPU | Proposal selection | 41.529 ms | 11.801 ms | 3.519x |
| CUDA | Total | 55.910 ms | 17.161 ms | 3.258x |
| CUDA | Backend evaluation | 9.922 ms | 5.421 ms | 1.830x |
| CUDA | Proposal selection | 46.331 ms | 11.761 ms | 3.939x |

Proposal selection improves **3.519x on
CPU** and **3.939x on CUDA**. Samplewise
median named-phase coverage remains 100.0% CPU and
99.9% CUDA, so the preregistered selection/coverage hypothesis
passes.

Total and backend medians also improve in this run, but the membership-index change
does not alter backend evaluation. Those changes and the improved ordinary controls
are retained as run-context evidence rather than attributed solely to the index.
The next measured host boundary is the packed evidence scan itself.

## Interpretation boundary

Phase medians come from separate distributions; component medians need not sum to
the total median. Index construction is outside retained intervals. This evidence
supports reusable membership validation, not one-shot latency, stochastic search,
compiler throughput, synthesis, or superoptimizer performance.
