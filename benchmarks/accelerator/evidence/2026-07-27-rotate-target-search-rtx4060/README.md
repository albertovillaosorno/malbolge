# Rotate-target search CPU/CUDA evidence

This directory retains a deterministic comparison of the identical
`classic-rotate-target-search-v1` workload through the exact CPU reference and
live CUDA backends. The corpus contains every classic word from 0 through 59,048,
the evaluation budget is 59,049, the seed is 17, and the target is 19,683.

The benchmark was executed from a clean detached worktree at source commit
`6d558eb72429df4082ad591800415c2a287614ed`. CUDA adapter creation and NVRTC/module setup occur before the timed
samples. Each retained interval includes canonical problem decoding, exact
stable-first duplicate pruning, candidate batch construction, backend evaluation,
and proposal selection. Proposal equality and independent CPU admission are
checked after every timed search.

## Protocol

- benchmark record: `benchmark.toml`
- experiment run: `experiment.toml`
- raw samples: `raw.csv`
- structured benchmark output: `throughput.json`
- warmup: one identical untimed search per backend
- retained samples: 15 per backend
- ordering: fixed interleaved CPU then CUDA
- outlier policy: retain all
- center: median
- dispersion/uncertainty: observed minimum-to-maximum range
- `throughput.json` SHA-256: `7b7d692074049f461bddb0957fcd8d3aeea806c463ac1ad4096508b49ad827d3`
- `raw.csv` SHA-256: `3cf6d68e315508a5bd0d319e5eb7af309ec867756d702827d4b45356b4fce20e`

## Environment

- host: Microsoft Windows 10.0.26200 x86-64
- Python: 3.14.6, repository-pinned installation
- CUDA: 13.3 Update 1, repository-pinned toolkit
- NVIDIA driver: 610.47
- device: NVIDIA GeForce RTX 4060 (`sm_89`, 8,188 MiB)

## Result

| Backend | Median | Minimum | Maximum | Population standard deviation |
| --- | ---: | ---: | ---: | ---: |
| CPU reference | 401.185 ms | 318.003 ms | 623.408 ms | 98.663 ms |
| CUDA | 412.570 ms | 336.735 ms | 696.523 ms | 97.232 ms |

The observed CUDA/CPU median speedup is **0.972x**. CUDA is therefore
**2.8% slower by median wall time** for this complete search
route on this host. The preregistered speedup hypothesis is rejected for this
workload and device.

## Interpretation boundary

This negative result does not dispute exact CUDA primitive execution. Every CPU
and CUDA sample produced the same proposal and passed independent CPU admission.
It shows that this 59,049-item search route is not large or device-resident enough
to amortize its host-side decoding, pruning, payload construction, transfer, and
result-selection costs. The benchmark has no phase instrumentation, so it does
not assign the slowdown to one component or claim a kernel-only comparison.

This is one RTX 4060 development result for one bounded exact strategy. It is not
a general statement about CUDA search, stochastic optimization, Malbolge program
synthesis, or a future resident search pipeline.
