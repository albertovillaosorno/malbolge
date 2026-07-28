# Exact extrema-validation search throughput

This directory retains the full-domain prepared rotate workload after primitive
result validation changed from an interpreted per-value loop to exact tuple
minimum/maximum bounds. Negative and above-domain results still fail before packed
evidence construction. Selector, membership, resident CUDA, proposal identity, and
independent CPU admission proofs remain unchanged.

The run used clean source commit
`3d2d484a4b65108b7bf66769ad97b923af4acbdb`, one warmup, and 15 retained fixed-order
samples per route. Preparation and CUDA session construction are outside prepared
intervals; all samples are retained.

## Protocol

- benchmark record: `benchmark.toml`
- experiment run: `experiment.toml`
- raw samples: `raw.csv`
- structured output: `throughput.json`
- outlier policy: retain all
- center: median
- `throughput.json` SHA-256: `7ada340acc318a8784297be63c97af4335ab733cfc4ff6dba7375c0c874469d8`
- `raw.csv` SHA-256: `38c0451863eb5809e3f23e5ba24399cba940aeed2552235ec8d4d6d2a70f7a50`

## Proof identity

- membership entries: 59049
- selector positions: 1
- CUDA builds/evaluations/reuses: 1/16/15
- resident operation/words: `rotate`/59049

## Result

| Route | Direct-selection baseline | Extrema validation | Baseline/current |
| --- | ---: | ---: | ---: |
| CPU ordinary | 211.768 ms | 213.488 ms | 0.992x |
| CPU prepared | 15.266 ms | 14.058 ms | 1.086x |
| CUDA ordinary | 226.028 ms | 227.646 ms | 0.993x |
| CUDA prepared | 6.182 ms | 4.929 ms | 1.254x |

Prepared medians improve **1.086x CPU** and **1.254x CUDA**. CUDA prepared is
**2.852x faster** than same-run CPU. Ordinary controls are essentially flat/slightly slower, supporting
attribution to prepared result validation.

## Interpretation boundary

This evidence covers full result validation and packing, not an isolated min/max
microbenchmark. It is amortized prepared-search evidence, not one-shot, stochastic,
compiler, synthesis, or superoptimizer performance.
