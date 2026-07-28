# Compact prepared-membership crossover evidence

This directory retains the version-2 four-scale measurement of exact prepared
rotate-target search after replacing copied membership tuples with proof-bound,
identity-sorted references. The run also compares the active compact index with
the historical copied `(logical_id, payload)` `frozenset` in the same process.

The run used clean source commit
`fc150e98b674f384ebe7bf3e0288254fdebbb083` on one RTX 4060. Every timing metric has 15 retained samples; each
memory metric has five. Each lookup sample contains 4,096 exact
operations. No outliers were removed.

## Protocol

- benchmark record: `benchmark.toml`
- experiment run: `experiment.toml`
- structured output: `crossover.json`
- raw samples: `raw.csv`
- source commit: `source-commit.txt`
- `crossover.json` SHA-256:
  `17a57b6c85616716b422d22f82fc9d15399db81773c1ebbf5763da42dd037640`
- `raw.csv` SHA-256:
  `88e8df58a98d7c84b300048269512f24e724a14393ab177c30adb65d876e1350`
- aggregate workload SHA-256:
  `4448fd7594a50646c5da2ccea28b239fb80da4b16a005739f33db56ce5aa3777`

## Environment

- host: Microsoft Windows 10.0.26200 x86-64
- Python: 3.14.6, repository-pinned installation
- CUDA: 13.3 Update 1, repository-pinned toolkit
- NVIDIA driver: 610.47
- device: NVIDIA GeForce RTX 4060 (`sm_89`, 8,188 MiB)

## Proof identity

- compact membership:
  `identity-sorted-candidate-reference-binary-search-v1`
- copied-set baseline: `copied-identity-payload-frozenset-v1`
- ordinary validator: `u32le-broadword-domain-v1`
- prepared validator: `cpu-reference-packed-equality-v1`
- reference and membership counts equal every candidate scale
- selector count is exactly one at every scale
- fresh CUDA sessions prove builds/evaluations/packed/reuses = 1/1/1/0
- reused CUDA sessions prove builds/evaluations/packed/reuses = 1/17/17/16
- compact and copied models both prove exact hit and exact miss behavior
- every result preserves the proposal and independent trusted admission

## Route medians and crossover

| Candidates | Cold prepare | Warm prepare | Ordinary | Fresh build | Reuse | Cold runs | Warm runs |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 12.028 ms | 0.076 ms | 0.233 ms | 0.756 ms | 0.115 ms | 108 | 7 |
| 64 | 12.245 ms | 0.278 ms | 0.459 ms | 0.753 ms | 0.115 ms | 38 | 3 |
| 1,024 | 15.213 ms | 3.250 ms | 3.822 ms | 0.939 ms | 0.141 ms | 5 | 2 |
| 59,049 | 207.761 ms | 194.917 ms | 222.518 ms | 12.143 ms | 0.415 ms | 1 | 1 |

The observed warm crossover sequence is **7, 3, 2, 1** runs; the cold sequence
is **108, 38, 5, 1**. At full domain, warm preparation plus the first resident
search is 207.059 ms versus 222.518 ms ordinary, a
15.458 ms one-shot advantage. Cold preparation plus first search is
219.904 ms, a 2.614 ms observed advantage. The cold one-run
margin is host/run specific and is not attributed solely to membership compaction.

## Complete prepared-state memory

| Candidates | Compact retained | Version-1 retained | Reduction | Compact peak | Peak reduction |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0.002 MiB | 0.002 MiB | 9.28% | 0.002 MiB | 8.31% |
| 64 | 0.012 MiB | 0.017 MiB | 31.30% | 0.015 MiB | 26.45% |
| 1,024 | 0.183 MiB | 0.269 MiB | 31.98% | 0.230 MiB | 27.17% |
| 59,049 | 10.910 MiB | 16.063 MiB | 32.08% | 14.080 MiB | 26.05% |

At full domain, complete incremental prepared state retains
11,439,693 bytes (10.910
MiB), down from 16,843,645 bytes
(16.063 MiB). That saves 5,403,952 bytes
(5.154 MiB), a 32.083% reduction.
Peak allocation falls by 5,201,089 bytes (4.960 MiB), or
26.051%. Retained state falls from
285.249 to 193.732 bytes per candidate.

## Membership-component result

| Candidates | Compact retained | Copied-set retained | Reduction | Compact prepare | Copied prepare |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 848 B | 328 B | -158.54% | 0.0122 ms | 0.0028 ms |
| 64 | 1,408 B | 6,408 B | 78.03% | 0.0312 ms | 0.0125 ms |
| 1,024 | 9,152 B | 98,568 B | 90.72% | 0.2796 ms | 0.1564 ms |
| 59,049 | 473,352 B | 5,876,552 B | 91.95% | 15.8507 ms | 18.0266 ms |

The compact representation has fixed proof/object overhead and is larger at one
candidate. It becomes smaller by 64 candidates. At full domain it retains
473,352 bytes versus
5,876,552 bytes, a
91.945% reduction and
12.415x less retained allocation. Compact
component preparation is 15.8507 ms versus
18.0266 ms for the copied set, 1.137x faster
in this run.

## Lookup trade-off

| Candidates | Compact hit | Copied hit | Hit slowdown | Compact miss | Copied miss | Miss slowdown |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 577.5 ns | 263.8 ns | 2.19x | 476.3 ns | 205.4 ns | 2.32x |
| 64 | 1292.9 ns | 266.1 ns | 4.86x | 1080.4 ns | 202.6 ns | 5.33x |
| 1,024 | 1801.5 ns | 265.5 ns | 6.78x | 1999.8 ns | 204.1 ns | 9.80x |
| 59,049 | 2625.2 ns | 265.2 ns | 9.90x | 2785.1 ns | 201.0 ns | 13.86x |

At full domain, exact compact hit lookup is
2625.2 ns versus
265.2 ns for the copied set, a
9.898x slowdown. Exact miss lookup is
2785.1 ns versus
201.0 ns, a
13.856x slowdown. The compaction is therefore
a memory/preparation optimization at scale, not a lookup-speed optimization.

## Decision and interpretation boundary

The compact proof-bound index is promoted for prepared search because it removes
most duplicate membership allocation, reduces complete prepared-state memory by
32.083% at full domain, improves component preparation, preserves exact
anti-fabrication behavior, and retains a finite strict CUDA crossover. The lookup
regression remains an explicit cost. Future work may reduce it only while keeping
batch proof identity and byte-exact payload checks.

`tracemalloc` covers incremental Python allocations only. It excludes the
prebuilt workload, process-wide rotate table, CUDA allocations, native ctypes
storage, imports, and adapter/NVRTC setup. Version-1 full-state numbers are a
retained prior-run control; component compact/copied measurements are same-run.
This is deterministic rotate-target evidence, not synthesis, stochastic search,
compiler, ROCm, multi-device, or cross-host evidence.
