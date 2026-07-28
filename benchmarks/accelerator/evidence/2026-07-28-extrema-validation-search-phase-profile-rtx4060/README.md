# Exact extrema-validation phase profile

This directory retains prepared-search phases after exact primitive domain checking
changed to tuple extrema. All selector/index/session proofs and exact proposal/CPU
admission checks remain active.

The run used clean source commit
`3d2d484a4b65108b7bf66769ad97b923af4acbdb`, one warmup, and 15 retained interleaved
profiles per backend. All samples are retained.

## Protocol

- benchmark record: `benchmark.toml`
- experiment run: `experiment.toml`
- raw samples: `raw.csv`
- structured output: `phases.json`
- outlier policy: retain all
- center: median
- `phases.json` SHA-256: `8396df12c3af5f09ab0b5473f6bf3aebbc7e3f48d9244d796c195efc674f657f`
- `raw.csv` SHA-256: `b4083aa6442d3dde0bb785dccab4f0748290035611cd2c6d88e73c05f1160944`

## Median comparison

| Backend | Phase | Direct-selection baseline | Extrema validation | Baseline/current |
| --- | --- | ---: | ---: | ---: |
| CPU | Total | 14.413 ms | 13.223 ms | 1.090x |
| CPU | Backend evaluation | 14.387 ms | 13.190 ms | 1.091x |
| CPU | Proposal selection | 13.200 us | 12.700 us | 1.039x |
| CUDA | Total | 5.267 ms | 3.967 ms | 1.328x |
| CUDA | Backend evaluation | 5.239 ms | 3.940 ms | 1.330x |
| CUDA | Proposal selection | 12.400 us | 11.800 us | 1.051x |

Backend evaluation improves **1.091x CPU** and **1.330x CUDA**. Samplewise median
named coverage remains 100.0% CPU and 99.8% CUDA, so the preregistered hypothesis
passes. Selection remains microsecond-scale.

## Interpretation boundary

The remaining CPU backend is dominated by rotate arithmetic; CUDA remains dominated
by host tuple/materialization plus packing rather than kernel or transfer. Phase
medians are separate distributions and need not sum to total median.
