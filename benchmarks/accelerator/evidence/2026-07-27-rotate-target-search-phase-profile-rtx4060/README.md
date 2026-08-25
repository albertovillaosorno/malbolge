# Rotate-target search phase profile

This directory retains diagnostic phase measurements for the identical complete
59,049-word `classic-rotate-target-search-v1` workload on the exact CPU reference
and live CUDA backend. Every profile produced the expected proposal and passed
independent CPU admission.

The run used a clean detached worktree at source commit
`d8460dd1bc55ad01a9f48a98d1f302b07aed681f`. Adapter/NVRTC setup is outside the retained intervals. One warmup and
15 retained profiles were executed for CPU, followed by one warmup and 15 retained
profiles for CUDA. The fixed backend blocks and diagnostic instrumentation mean
this evidence is for phase attribution, not a replacement CPU/CUDA speedup claim.
The interleaved ordinary-throughput comparison remains separately retained under

`../2026-07-27-rotate-target-search-rtx4060/`.

## Protocol

- benchmark record: `benchmark.toml`
- experiment run: `experiment.toml`
- raw samples: `raw.csv`
- structured output: `phases.json`
- warmup: one profiled search per backend
- retained profiles: 15 per backend
- ordering: complete CPU block, then complete CUDA block
- outlier policy: retain all
- center: median
- dispersion/uncertainty: observed minimum-to-maximum range
- `phases.json` SHA-256: `c2c5019b019cc3aee38d2d277abf1e55202f271d0c1b91c366a51e3e946c3b98`
- `raw.csv` SHA-256: `246c12faeabf111959d4def9c3b13697dc952dc0547a3a66ae63f10322ea55f0`

## Environment

- host: Microsoft Windows 10.0.26200 x86-64
- Python: 3.14.6, repository-pinned installation
- CUDA: 13.3 Update 1, repository-pinned toolkit
- NVIDIA driver: 610.47
- device: NVIDIA GeForce RTX 4060 (`sm_89`, 8,188 MiB)

## Median phase attribution

| Backend | Total | Batch build | Backend evaluation | Proposal selection | Named-phase coverage |
| --- | ---: | ---: | ---: | ---: | ---: |
| CPU reference | 340.470 ms | 132.653 ms | 132.738 ms | 52.029 ms | 97.5% |
| CUDA | 326.535 ms | 123.682 ms | 138.703 ms | 49.399 ms | 99.5% |

Named phases explain more than 97% of median total time on both backends, so the
attribution hypothesis passes. For CUDA, host-side phases account for about 57.0%
of median total time while backend evaluation accounts for about 42.5%. Batch
construction and proposal selection alone consume about
173.081 ms at their medians.

## Interpretation

The current route rebuilds the complete encoded candidate batch and repeats
host-side proposal selection for every search. Those costs are large enough that
optimizing only the CUDA kernel cannot produce a strong end-to-end improvement.
The next evidence-driven target is reusable validated search input/batch state,
followed by a resident or fused evaluation/selection path if equivalence remains
explicit.

CPU and CUDA totals in this diagnostic run must not be used to overturn the
separate interleaved throughput result. Block ordering, instrumentation overhead,
and run-to-run system noise differ. This record identifies where time is spent;
it does not establish a new backend winner.
