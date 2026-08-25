# Exact candidate subset evidence

This bundle retains candidate-subset proof tradeoff version 1, crossover protocol
version 9, prepared-search throughput version 3, and prepared phase profile
version 3. It compares the proof-bound request-order position subset with repeated
membership validation and preserves the immediate projected-rotate v8 baseline.

## Provenance

- implementation commit: `c3cb002416935335dec860e4402592da95afa963`
- immediate baseline source commit: `59a88a3a89953b232d3220c0bf65b74d65c05b73`
- raw observations: `raw.csv` (1,400 rows)
- aggregate workload SHA-256: `4448fd7594a50646c5da2ccea28b239fb80da4b16a005739f33db56ce5aa3777`
- `raw.csv` SHA-256: `3a2e948b5cd1e8c58f2d30879ab8f4c53089c21c194f620892925e38865d85f7`
- `candidate-subset.json` SHA-256: `a9e528200be316d559df7a86556e53996941abe5408303997c2297053674bc54`
- `crossover.json` SHA-256: `2b3addd81ad5dce6570ec9f42bc410a415a48618b67269588d8774d21dfd281e`
- `throughput.json` SHA-256: `d4a31a2712dbdf1e33bf3382c1b67adb850e44b993fb5b94f3cffd786000e43f`
- `phases.json` SHA-256: `f8b77d0ec5eb08b981cdf5a622d88b5ba82f4fd04b2b86dc3b3cf5654635f5fa`
- `baseline-crossover.json` SHA-256: `d3b27d2e00fee026449b679ad954e207625561679cc10566a92d530fc14720f2`
- `baseline-throughput.json` SHA-256: `c6a59532ff05d2ac12d253ec7b39020e028194566ef99074b06aa1b5eee62d13`
- `baseline-phases.json` SHA-256: `346e4f6686d1c03ddac0e32927076f5b2bd871136bfa2ff77b5f5efa07a6008a`

## Environment

- host: Microsoft Windows 10.0.26200 x86-64
- Python: 3.14.6, repository-pinned installation
- CUDA: 13.3 Update 1
- NVIDIA driver: 610.47
- device: NVIDIA GeForce RTX 4060 (`sm_89`, 8,188 MiB)

## Proofs

- candidate subset: `request-order-position-subset-v1`
- projected execution: `classic-rotate-preimage-position-subset-v2`
- selector: `classic-u32le-native-view-preimage-v2`
- batch builder: `classic-u32le-bitset-inplace-first-representatives-v2`
- prepared reference: `cpu-scalar-packed-equality-v2`
- prepared input: `proof-bound-u32le-primitive-input-v1`
- candidate storage: `u32-index-fixed-width-payloads-rotation-v1`
- membership: `u32-rotation-or-pair-or-reference-binary-search-v1`
- ordinary validator: `u32le-broadword-domain-v1`
- zero, one, and multi-item subsets retain exact request-order positions
- mutable, duplicate, reordered, out-of-range, forged, wrong-type, and cross-batch
  subset or projection state fails closed
- full-domain prepared execution retains 1 projected reference word, 59,049 full
  membership entries, and 1 selected position
- CPU session: 1 build, 16 evaluations, 15 reuses, 1 resident rotate word, and
  59,049 rotate-table entries
- CUDA session: 1 build, 16 evaluations, 16 packed evaluations, 15 reuses, and
  1 resident rotate word

## Exact subset construction

| Subset | Legacy | Proof | Change | Retained legacy/proof | Peak legacy/proof |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 2.3 us | 4.3 us | 0.535x | 704 / 848 B | 960 / 1,024 B |
| 1 | 20.0 us | 7.5 us | 2.667x | 1,111 / 1,095 B | 1,351 / 1,351 B |
| 64 | 1.0356 ms | 0.1581 ms | 6.550x | 10,176 / 10,160 B | 13,408 / 13,408 B |
| 1,024 | 16.8647 ms | 2.5298 ms | 6.666x | 148,502 / 148,422 B | 198,358 / 198,358 B |

The proof route is not an empty-subset speedup: its fixed proof object adds 2.0
microseconds, 144 retained bytes, and 64 peak bytes in that case. From one item
upward it is faster, and at 64 and 1,024 positions it is 6.550x and 6.666x faster
than reconstructing and revalidating every member.

## Projected rotate preservation

| Metric | Exact subset v9 | Projected v8 | Change |
| --- | ---: | ---: | ---: |
| full-domain cold preparation | 45.7698 ms | 46.2706 ms | 1.011x |
| full-domain warm preparation | 46.2938 ms | 46.6161 ms | 1.007x |
| retained state | 474,978 B | 475,010 B | 32 B lower |
| peak allocation | 710,126 B | 710,126 B | unchanged |
| cold/warm crossover | 1 / 1 runs | 1 / 1 runs | unchanged |

At one candidate, cold/warm crossover improves from 8/7 to 7/6. At 64 it stays
4/4. At 1,024 it improves from 2/1 to 1/1. The exact subset proof therefore
preserves or improves preparation economics at every retained scale.

## Throughput

| Route | Exact subset v9 | Projected v8 | Change |
| --- | ---: | ---: | ---: |
| CPU ordinary | 80.0024 ms | 80.0775 ms | 1.001x |
| CPU prepared | 0.0809 ms | 0.0787 ms | 0.973x |
| CUDA ordinary | 92.2213 ms | 92.6334 ms | 1.004x |
| CUDA prepared | 0.2729 ms | 0.2743 ms | 1.005x |

CPU prepared isolated throughput is 2.8% slower in this run. That regression is
retained rather than attributed away. CPU prepared phase total is exactly equal,
while CUDA prepared throughput is 0.5% faster. Ordinary routes are contextual
controls and are not attributed to the subset proof.

## Prepared phases

| Phase | CPU v8 | CPU v9 | CPU change | CUDA v8 | CUDA v9 | CUDA change |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| backend evaluation | 13.4 us | 13.4 us | 1.000x | 92.1 us | 93.1 us | 0.989x |
| total | 56.4 us | 56.4 us | 1.000x | 141.4 us | 141.1 us | 1.002x |

CPU total is exactly unchanged at 56.4 microseconds. CUDA total improves from
141.4 to 141.1 microseconds. The repeated hot path stores primitive state directly;
subset and projection proofs are validated and unwrapped once during preparation.

## Decision

`request-order-position-subset-v1` and
`classic-rotate-preimage-position-subset-v2` are promoted as exact authority for
prepared projected search. The result generalizes projection to zero, one, and
multiple request-order positions without replacing full membership, exact evidence,
proposal validation, or independent trusted admission. It is promoted for safety and
multi-item scaling, not as an empty-subset optimization. The isolated CPU prepared
throughput regression remains an explicit tradeoff because CPU phase total and all
preparation, memory, crossover, CUDA, and proof obligations are preserved. The next
production step is to apply this contract only when a real non-invertible or
multi-position strategy can supply exact positions; heuristic filtering remains

inadmissible.
