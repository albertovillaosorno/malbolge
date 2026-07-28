# Packed prepared-primitive crossover evidence

This bundle retains the version-4 proof-bound packed primitive-input result and
its immediate clean baseline. Prepared rotate input now reuses indexed candidate
payload bytes directly. CPU decodes once into a local resident tuple; CUDA copies
packed u32 little-endian words directly into its resident device session.

## Provenance

- implementation commit: `1deca088aca6f3a1aa862833bdbbcfb167b1a121`
- immediate baseline commit: `81d82cf0e10404c7b234ddfc27a1b1e4ba286815`
- benchmark: `benchmark.toml`
- run manifest: `experiment.toml`
- raw observations: `raw.csv` (1,200 rows)
- aggregate workload SHA-256: `4448fd7594a50646c5da2ccea28b239fb80da4b16a005739f33db56ce5aa3777`
- `raw.csv` SHA-256: `c1f56787b5395db8753e71869bc62935bcf5bfa9e1a02dedb381e70e37a20cd6`
- `crossover.json` SHA-256: `613e6777e5efedda24714a9e420c2b6773b4825189d3f0ffb5f623dc1929a223`
- `throughput.json` SHA-256: `90ddaf40e24abebfc723c0c6cba433cfe8f7990e9eb4b6b71a6423a685f6c138`
- `phases.json` SHA-256: `8b266ad49cba889d111424dd02287793b75b240b8882171c4ed61046f20411b7`
- `baseline-throughput.json` SHA-256: `5f96c181d9295584f71fd7311d4b6115fb3b8b1d747124ff3a9e63b60a1f5b24`
- `baseline-phases.json` SHA-256: `cd4be65a9aa338031a09ba5463a23ff68815027250a02168aed989b9441da5a2`

## Environment

- host: Microsoft Windows 10.0.26200 x86-64
- Python: 3.14.6, repository-pinned installation
- CUDA: 13.3 Update 1
- NVIDIA driver: 610.47
- device: NVIDIA GeForce RTX 4060 (`sm_89`, 8,188 MiB)

## Proofs

- prepared primitive storage: `proof-bound-u32le-primitive-input-v1`
- candidate storage: `u32-index-fixed-width-payloads-rotation-v1`
- membership: `u32-rotation-or-pair-or-reference-binary-search-v1`
- ordinary validator: `u32le-broadword-domain-v1`
- prepared validator: `cpu-reference-packed-equality-v1`
- CPU session: 1 build, 16 evaluations, 15 reuses, 59,049 resident words,
  rotate kind, and 59,049 table entries
- CUDA session: 1 build, 16 evaluations, 15 reuses, 16 packed evaluations,
  59,049 resident words, and rotate kind
- exact proposal, independent trusted admission, reference count, membership
  count, and selector count pass every retained route

## Prepared-state memory and crossover

At 59,049 candidates, incremental retained prepared state falls from
3,064,623 bytes (2.923
MiB) to 713,791 bytes (0.681 MiB), a
**76.709% reduction**. Retained state is
12.088 bytes per candidate.

Peak allocation remains 8,802,328 bytes
(8.395 MiB), unchanged from the baseline. Preparation still
builds a temporary CPU reference/decode tuple; the change removes retained tuple
ownership, not that transient peak. Full-domain cold/warm crossover remains
**1/1**. Warm
preparation is 109.027 ms and ordinary CUDA is
142.008 ms.

## Throughput comparison

| Route | Packed v4 | Baseline v3 | Speedup |
| --- | ---: | ---: | ---: |
| CPU ordinary | 132.848 ms | 139.517 ms | 1.050x |
| CPU prepared | 3.261 ms | 3.316 ms | 1.017x |
| CUDA ordinary | 144.440 ms | 152.055 ms | 1.053x |
| CUDA prepared | 0.429 ms | 0.449 ms | 1.047x |

Packed storage does not trade retained memory for hot-route regression. Prepared
CPU improves 1.017x and prepared CUDA improves
1.047x in the clean comparison. CPU tuple decode
is outside measured reuse intervals after the one warmup/build.

## Phase attribution

| Backend | Phase | Packed v4 | Baseline v3 | Speedup |
| --- | --- | ---: | ---: | ---: |
| CPU | backend evaluation | 2.9161 ms | 2.9311 ms | 1.005x |
| CPU | total | 2.9664 ms | 2.9842 ms | 1.006x |
| CUDA | backend evaluation | 0.2141 ms | 0.2290 ms | 1.070x |
| CUDA | total | 0.2654 ms | 0.2918 ms | 1.099x |

The clearest phase change is CUDA total prepared search, which improves
1.099x. CPU total is essentially flat-to-
slightly-positive at 1.006x, as intended for
a resident decode cache preserving the existing table path.

## Decision and boundary

The packed prepared primitive representation is promoted. It removes 76.709% of
retained prepared-state memory at full domain, preserves one-run crossover, proves
one decode/build plus fifteen reuses on both CPU and CUDA, and does not regress any
of the four clean throughput routes.

The unchanged peak is retained as a negative boundary. A future change may avoid
the temporary CPU reference/decode tuple during preparation only if it keeps an
independent exact reference and the same corruption/fabrication failures. This is
not evidence for synthesis, stochastic search, compiler behavior, ROCm,
multi-device execution, or cross-host portability.
