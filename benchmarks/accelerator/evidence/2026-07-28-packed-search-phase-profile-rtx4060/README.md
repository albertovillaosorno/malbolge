# Packed prepared-search phase profile

This directory retains post-preparation phase attribution after primitive candidate
results changed from one object and bytes payload per candidate to one fixed-width
packed buffer. The complete 59,049-word rotate-target workload, strategy-bound
prepared state, proposal identity, and independent CPU admission remain unchanged.

The run used a clean detached worktree at source commit
`01a211f5008c3bd5be4b77a770e6e2cb0e5a1789` and repeats the protocol from
`../2026-07-28-prepared-search-phase-profile-rtx4060/`. Preparation, CUDA adapter
construction, and NVRTC setup are outside retained intervals. One warmup precedes
15 fixed interleaved CPU-then-CUDA profiles.

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
- `phases.json` SHA-256: `a54c148a932b103b8f1f4f340cbbd3157700c18893ab6ea8efadf87cabb9385e`
- `raw.csv` SHA-256: `b2c02233954c51ea7f4a8741900e4166c26c73b44fcaa13c1fa152ad70027c5e`

## Environment

- host: Microsoft Windows 10.0.26200 x86-64
- Python: 3.14.6, repository-pinned installation
- CUDA: 13.3 Update 1, repository-pinned toolkit
- NVIDIA driver: 610.47
- device: NVIDIA GeForce RTX 4060 (`sm_89`, 8,188 MiB)

## Median phase comparison

| Backend | Phase | Pre-packed | Packed | Pre-packed/packed |
| --- | --- | ---: | ---: | ---: |
| CPU | Total | 156.935 ms | 76.347 ms | 2.056x |
| CPU | Backend evaluation | 125.412 ms | 53.907 ms | 2.326x |
| CPU | Proposal selection | 30.796 ms | 22.502 ms | 1.369x |
| CUDA | Total | 170.276 ms | 89.624 ms | 1.900x |
| CUDA | Backend evaluation | 138.320 ms | 67.202 ms | 2.058x |
| CUDA | Proposal selection | 31.912 ms | 22.288 ms | 1.432x |

Backend-evaluation medians are lower on both backends. The samplewise median of
named-phase coverage is **100.0% for CPU** and **100.0% for CUDA**, so the
preregistered packed-phase hypothesis passes.

After packing, backend evaluation still dominates: about **70.6% of CPU** and
**75.0% of CUDA** median total time. Proposal selection accounts for about
**29.5%** and **24.9%**.
The next measured boundary is now request payload decoding/batch validation and the
primitive backend transfer path, rather than evidence-object materialization.

## Interpretation boundary

This evidence compares complete instrumented phase paths, not isolated allocation
microbenchmarks. Packed representation also removes logical-ID tuple reconstruction
from result validation and changes selector iteration. The result therefore belongs
to the complete representation change.

Prepared-state construction is excluded. These totals do not establish a CUDA
advantage, resident device search, stochastic optimization, compiler throughput,
or superoptimizer performance.
