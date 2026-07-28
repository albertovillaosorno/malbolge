# Direct prepared rotate-selection throughput

This directory retains the complete 59,049-word rotate-target workload after
prepared selection began storing the evaluated position of the unique classic
rotate preimage. Prepared CPU and CUDA read and verify only that packed evidence
word. Ordinary routes retain the full evidence scan. Every sample preserves exact
proposal identity and independent CPU admission.

The run used a clean detached worktree at source commit
`e36d33f6042842932ba41f0be11850e615457937`. One warmup precedes 15 fixed
interleaved CPU ordinary, CPU prepared, CUDA ordinary, and CUDA prepared samples.
Preparation, inverse-position lookup,
membership indexing, CUDA adapter construction, NVRTC, and the first resident build
are outside retained prepared intervals.

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
- `throughput.json` SHA-256: `8115b41718bfe6569c708029c61dfc760080bbf47b71b6fd9c7eacb20d482022`
- `raw.csv` SHA-256: `b6245359f1108df795202ba5d64bfca84d3f1afa798a916834ead1cf886aa772`

## Environment

- host: Microsoft Windows 10.0.26200 x86-64
- Python: 3.14.6, repository-pinned installation
- CUDA: 13.3 Update 1, repository-pinned toolkit
- NVIDIA driver: 610.47
- device: NVIDIA GeForce RTX 4060 (`sm_89`, 8,188 MiB)

## Prepared-proof identity

The benchmark failed closed unless it observed:

- membership index entries: 59049
- exact prepared selector positions: 1
- CUDA session builds: 1
- CUDA session evaluations: 16
- CUDA session reuses: 15
- resident operation/words: `rotate`/59049

## Result

| Route | Indexed baseline | Direct selection | Baseline/current |
| --- | ---: | ---: | ---: |
| CPU ordinary | 216.529 ms | 211.768 ms | 1.022x |
| CPU prepared | 26.797 ms | 15.266 ms | 1.755x |
| CUDA ordinary | 229.386 ms | 226.028 ms | 1.015x |
| CUDA prepared | 17.970 ms | 6.182 ms | 2.907x |

Direct selection improves CPU prepared **1.755x** and CUDA prepared **2.907x**,
so the preregistered prepared-route hypothesis passes. CUDA prepared is **2.470x
faster** than same-run CPU.

Ordinary controls improve only 1.022x CPU and 1.015x CUDA. The much larger prepared
reductions, together
with the phase sibling, support attribution to prepared direct selection.

## Interpretation boundary

This is amortized repeated-search evidence after untimed strategy preparation. It
does not measure inverse-position construction or one-shot latency. The optimization
is specific to the proven classic rotate bijection and still verifies backend
evidence at the retained position. It is not stochastic search, compiler throughput,
synthesis, or superoptimizer evidence.
