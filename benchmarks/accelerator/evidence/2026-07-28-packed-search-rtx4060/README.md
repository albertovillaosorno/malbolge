# Packed candidate-evidence search throughput

This directory retains the complete 59,049-word rotate-target search after
replacing per-candidate `CandidateEvidence` objects and four-byte payload objects
with one fixed-width packed evidence buffer. Logical identity remains inherited
from validated request order. Generic item-form results remain supported, and
every retained route produces the expected proposal plus independent CPU
admission.

The run used a clean detached worktree at source commit
`01a211f5008c3bd5be4b77a770e6e2cb0e5a1789`. It repeats the identical protocol and workload from
`../2026-07-28-prepared-search-rtx4060/`: preparation, CUDA adapter construction,
and NVRTC setup are outside timed intervals; one warmup precedes 15 fixed
interleaved CPU ordinary, CPU prepared, CUDA ordinary, and CUDA prepared samples.

## Protocol

- benchmark record: `benchmark.toml`
- experiment run: `experiment.toml`
- raw samples: `raw.csv`
- structured output: `throughput.json`
- warmup: one execution per route
- retained samples: 15 per route
- ordering: fixed interleaved four-route sequence
- preparation timed: no
- outlier policy: retain all
- center: median
- dispersion/uncertainty: observed minimum-to-maximum range
- `throughput.json` SHA-256: `854184aadfcad5c9bb2ec8806055d694d719295bc1e7b3148030a14b451a995c`
- `raw.csv` SHA-256: `0339b6ce4713a34b2b349dce706dc81d1c76f973b7d65d61528eec38ab0ff673`

## Environment

- host: Microsoft Windows 10.0.26200 x86-64
- Python: 3.14.6, repository-pinned installation
- CUDA: 13.3 Update 1, repository-pinned toolkit
- NVIDIA driver: 610.47
- device: NVIDIA GeForce RTX 4060 (`sm_89`, 8,188 MiB)

## Result

| Route | Pre-packed median | Packed median | Pre-packed/packed |
| --- | ---: | ---: | ---: |
| CPU ordinary | 293.564 ms | 211.693 ms | 1.387x |
| CPU prepared | 148.590 ms | 77.308 ms | 1.922x |
| CUDA ordinary | 306.872 ms | 230.144 ms | 1.333x |
| CUDA prepared | 162.693 ms | 91.199 ms | 1.784x |

All four medians are lower, so the preregistered packed-representation hypothesis
passes on this host. Within the packed implementation, prepared state remains
beneficial: **2.738x on CPU** and **2.524x on CUDA** relative to their ordinary
routes.

Packed CUDA prepared remains slower than packed CPU prepared. The observed
CPU-prepared/CUDA-prepared ratio is **0.848x**, so CUDA is about **18.0% slower by
median wall time**. Packing removes a
large host representation cost; it does not establish a CUDA advantage.

## Interpretation boundary

This comparison attributes improvement to the complete code change, not solely to
one allocation primitive. Packed evidence also changes result-order validation and
selector consumption. The retained phase record in the sibling packed profile
identifies where time remains.

Prepared medians are amortized repeated-search measurements and exclude one-time
preparation. The result is not compiler throughput, stochastic search, Malbolge
program synthesis, a resident device corpus, or a superoptimizer speedup.
