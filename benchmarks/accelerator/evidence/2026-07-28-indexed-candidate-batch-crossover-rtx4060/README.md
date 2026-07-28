# Indexed candidate-batch crossover evidence

This directory retains the version-3 four-scale measurement after replacing
per-candidate Python IDs, objects, and payloads with proof-carrying fixed-width
storage. The active membership index reuses one validated logical-index rotation
instead of retaining another sorted reference or pair array. Ordinary proposal
selection and admission use indexed evidence/lookup directly.

The run used clean source commit
`81d82cf0e10404c7b234ddfc27a1b1e4ba286815` on one RTX 4060. Every timing metric has 15 retained samples; every
memory metric has five. Each lookup sample contains 4,096 exact
operations. No outliers were removed.

## Protocol

- benchmark record: `benchmark.toml`
- experiment run: `experiment.toml`
- structured output: `crossover.json`
- raw samples: `raw.csv`
- source commit: `source-commit.txt`
- `crossover.json` SHA-256:
  `ad70ad7d7630b17b3ec600391c98146442004ac709bc0d2abbdd9bad228dc999`
- `raw.csv` SHA-256:
  `7162642e623f9f24e1aea2e829c1bf80ee1538f488c445d5659b9f95bae52c0c`
- aggregate workload SHA-256:
  `4448fd7594a50646c5da2ccea28b239fb80da4b16a005739f33db56ce5aa3777`

## Environment

- host: Microsoft Windows 10.0.26200 x86-64
- Python: 3.14.6, repository-pinned installation
- CUDA: 13.3 Update 1, repository-pinned toolkit
- NVIDIA driver: 610.47
- device: NVIDIA GeForce RTX 4060 (`sm_89`, 8,188 MiB)

## Proof identity

- candidate storage: `u32-index-fixed-width-payloads-rotation-v1`
- membership: `u32-rotation-or-pair-or-reference-binary-search-v1`
- copied-set baseline: `copied-identity-payload-frozenset-v1`
- ordinary validator: `u32le-broadword-domain-v1`
- prepared validator: `cpu-reference-packed-equality-v1`
- reference and membership counts equal every candidate scale
- selector count is exactly one at every scale
- fresh CUDA sessions prove builds/evaluations/packed/reuses = 1/1/1/0
- reused CUDA sessions prove builds/evaluations/packed/reuses = 1/17/17/16
- exact proposal identity and trusted independent admission pass every sample
- ordinary indexed admission rejects payload substitution without a materialized
  identity/payload table

## Route medians and crossover

| Candidates | Cold prepare | Warm prepare | Ordinary | Fresh build | Reuse | Cold runs | Warm runs |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 12.137 ms | 0.088 ms | 0.255 ms | 0.742 ms | 0.127 ms | 100 | 6 |
| 64 | 12.374 ms | 0.212 ms | 0.429 ms | 0.820 ms | 0.136 ms | 45 | 4 |
| 1,024 | 14.166 ms | 2.071 ms | 2.861 ms | 0.944 ms | 0.153 ms | 6 | 2 |
| 59,049 | 132.553 ms | 117.753 ms | 152.998 ms | 11.755 ms | 0.405 ms | 1 | 1 |

At full domain, warm preparation plus first resident search is
129.508 ms versus 152.998 ms ordinary,
a 23.490 ms one-shot advantage. Cold preparation
plus first search is 144.308 ms, still
8.691 ms faster than ordinary. Full-domain
cold/warm crossover remains **1/1**. Small scales retain fixed proof/object overhead:
64-candidate crossover moves from 38/3 in version 2 to 45/4 here, and the
1-candidate prepared memory grows slightly.

## Version-2 baseline comparison

| Candidates | Warm-prepare speedup | Ordinary speedup | Retained reduction | Peak reduction |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 0.866x | 0.911x | -4.93% | -12.42% |
| 64 | 1.313x | 1.070x | 72.11% | 61.09% |
| 1,024 | 1.569x | 1.336x | 75.33% | 46.42% |
| 59,049 | 1.655x | 1.454x | 73.21% | 40.38% |

At 59,049 candidates, warm preparation falls from
194.917 to 117.753 ms
(1.655x), cold preparation from
207.761 to 132.553 ms
(1.567x), and ordinary CUDA search from
222.518 to 152.998 ms
(1.454x).

Complete prepared state retains 3,064,623 bytes
(2.923 MiB), down from
11,439,693 bytes
(10.910 MiB). That saves 8,375,070 bytes
(7.987 MiB), a 73.211% reduction.
Peak allocation falls by 5,961,252 bytes (5.685 MiB), or
40.378%. Retained state falls from
193.732 to
51.900 bytes per candidate.

## Membership/storage component

| Candidates | Active retained | Version-2 compact | Copied-set retained | Active prepare | Copied prepare |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 528 B | 848 B | 869 B | 0.0084 ms | 0.0112 ms |
| 64 | 528 B | 1,408 B | 12,458 B | 0.0081 ms | 0.1542 ms |
| 1,024 | 528 B | 9,152 B | 189,154 B | 0.0099 ms | 2.4930 ms |
| 59,049 | 528 B | 473,352 B | 11,180,412 B | 0.0177 ms | 155.4303 ms |

At full domain, the active rotation-backed membership component retains 528 bytes,
versus 473,352 bytes for version 2 and 11,180,412 bytes for the same-run copied
set. That is 99.888% below version 2 and
99.995% below the copied set. Active
component preparation is 0.0177 ms, versus
15.8507 ms in version 2 and
155.4303 ms copied: 895.520x
and 8781.373x advantages respectively.

## Lookup trade-off

| Candidates | Active hit | Version-2 hit | Copied hit | Active miss | Version-2 miss |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 2621.1 ns | 577.5 ns | 262.7 ns | 632.6 ns | 476.3 ns |
| 64 | 9876.6 ns | 1292.9 ns | 269.0 ns | 631.7 ns | 1080.4 ns |
| 1,024 | 13676.4 ns | 1801.5 ns | 263.4 ns | 636.4 ns | 1999.8 ns |
| 59,049 | 17755.3 ns | 2625.2 ns | 265.6 ns | 635.6 ns | 2785.1 ns |

The retained cost is hit latency. At full domain, an active exact hit takes
17.755 microseconds, versus
2.625 microseconds in version 2 and
0.266 microseconds for the copied set. That
is 6.763x slower than version 2 and
66.844x slower than the copied set. Exact miss
lookup improves from 2.785 to
0.636 microseconds
(4.382x), but remains
3.094x slower than copied-set miss lookup.
Only one proposal is admitted in this workload, so full-route results include this
cost rather than extrapolating 4,096 repeated hits.

## Decision and interpretation boundary

Fixed-width indexed candidate storage and rotation-backed membership are promoted
for large deterministic batches. They reduce full prepared retention by 73.211%,
peak allocation by 40.378%, and improve full-domain warm preparation and ordinary
search by 1.655x and 1.454x while preserving one-run cold/warm crossover. The
promotion is not universal: tiny batches have fixed overhead and exact hit lookup
is slower. Ordinary tuple batches and arbitrary indexed batches retain exact
reference/pair fallbacks.

`tracemalloc` covers incremental Python allocations only. It excludes the
prebuilt workload, process-wide rotate table, CUDA allocations, native ctypes
storage, imports, and adapter/NVRTC setup. Version-2 full-state numbers are a
retained prior-run control; active/copied component measurements are same-run.
The next retained-memory boundary is the prepared primitive Python integer tuple.
This evidence does not establish synthesis, stochastic search, compiler, ROCm,
multi-device, or cross-host behavior.
