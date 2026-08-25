# Projected prepared rotate evidence

This bundle retains crossover protocol version 8, prepared-search throughput version
2, and prepared phase profile version 2. The prepared rotate strategy evaluates only
the selector-proven exact preimage while full-batch membership and trusted admission
remain authoritative.

## Provenance

- implementation commit: `59a88a3a89953b232d3220c0bf65b74d65c05b73`
- immediate baseline source commit: `5d8cff5fb01462cd9885d521d7b9aec2d6b79890`
- raw observations: `raw.csv` (1,200 rows)
- aggregate workload SHA-256: `4448fd7594a50646c5da2ccea28b239fb80da4b16a005739f33db56ce5aa3777`
- `raw.csv` SHA-256: `7d3f769583d8a34d1693186c84eb6378271c666b8a3188b8632cf3ca0d9b7c4f`
- `crossover.json` SHA-256: `d3b27d2e00fee026449b679ad954e207625561679cc10566a92d530fc14720f2`
- `throughput.json` SHA-256: `c6a59532ff05d2ac12d253ec7b39020e028194566ef99074b06aa1b5eee62d13`
- `phases.json` SHA-256: `346e4f6686d1c03ddac0e32927076f5b2bd871136bfa2ff77b5f5efa07a6008a`
- `baseline-crossover.json` SHA-256: `1cc066fea82288707cb115ffb233b9ac34d6848e68a66f4e6f2b17600713704e`
- `baseline-throughput.json` SHA-256: `aae643cee54d04d404681e25ef951961f3b7ce3c96fc9a93a7a8e67bec1f20b6`
- `baseline-phases.json` SHA-256: `d26a3a727c8217dfbc095892ea4e4157dfd348abecac78122f84c16beea38d6a`

## Environment

- host: Microsoft Windows 10.0.26200 x86-64
- Python: 3.14.6, repository-pinned installation
- CUDA: 13.3 Update 1
- NVIDIA driver: 610.47
- device: NVIDIA GeForce RTX 4060 (`sm_89`, 8,188 MiB)

## Proofs

- projected execution: `classic-rotate-preimage-projection-v1`
- selector: `classic-u32le-native-view-preimage-v2`
- batch builder: `classic-u32le-bitset-inplace-first-representatives-v2`
- prepared reference: `cpu-scalar-packed-equality-v2`
- prepared input: `proof-bound-u32le-primitive-input-v1`
- candidate storage: `u32-index-fixed-width-payloads-rotation-v1`
- membership: `u32-rotation-or-pair-or-reference-binary-search-v1`
- ordinary validator: `u32le-broadword-domain-v1`
- canonical full-domain counts: 1 projected reference word, 59,049 full membership entries, and 1 selected position
- CPU session: 1 build, 16 evaluations, 15 reuses, 1 resident rotate word, and 59,049 rotate-table entries
- CUDA session: 1 build, 16 evaluations, 16 packed evaluations, 15 reuses, and 1 resident rotate word
- empty projection skips backend execution; wrong evaluator, fabricated member, oversized projection, forged proof, wrong exact evidence, and fabricated proposal fail closed

## Full-domain preparation economics

| Metric | Projected v8 | Full prepared v7 | Change |
| --- | ---: | ---: | ---: |
| cold preparation | 46.2706 ms | 64.4648 ms | 1.393x |
| warm preparation | 46.6161 ms | 64.7804 ms | 1.390x |
| retained state | 475,010 B | 710,647 B | 33.158% lower |
| peak allocation | 710,126 B | 946,675 B | 24.987% lower |
| reference bytes | 4 B | 236,196 B | 59,049x smaller |
| CUDA resident input+output | 8 B | 472,392 B | 59,049x smaller |
| cold/warm crossover | 1 / 1 runs | 1 / 1 runs | unchanged |

At 1,024 candidates, retained state falls from 14,315 to 10,810 bytes and warm
crossover moves from 2 to 1. At 64 candidates crossover remains 4/4. At one
candidate, retained state rises from 1,863 to 2,349 bytes and crossover moves from
6/6 to 8/7, so projection is not a universal tiny-batch win.

## Throughput

| Route | Projected | Immediate baseline | Change |
| --- | ---: | ---: | ---: |
| CPU ordinary | 80.0775 ms | 83.3013 ms | 1.040x |
| CPU prepared | 0.0787 ms | 3.2402 ms | **41.172x** |
| CUDA ordinary | 92.6334 ms | 96.0232 ms | 1.037x |
| CUDA prepared | 0.2743 ms | 0.5116 ms | **1.865x** |

Ordinary changes are controls and are not attributed to projection. Within the
projected run, CPU prepared is 1017.5x faster than CPU ordinary, and CUDA prepared is
337.7x faster than CUDA ordinary.

## Prepared phases

| Phase | CPU baseline | CPU projected | CPU speedup | CUDA baseline | CUDA projected | CUDA speedup |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| backend evaluation | 2.9266 ms | 0.0134 ms | **218.4x** | 0.2179 ms | 0.0921 ms | **2.366x** |
| total | 2.9799 ms | 0.0564 ms | **52.8x** | 0.2707 ms | 0.1414 ms | **1.914x** |

Prepared validation grows by 0.0004 ms on CPU and improves by 0.0001 ms on CUDA;
proposal selection and result validation remain small. The speedup is localized to
the backend phase exactly as predicted by the projected work reduction.

## Decision

Selection-aware exact projection is promoted for classic rotate prepared search. It
evaluates only the proof-relevant zero-or-one preimage, yet full membership and
independent trusted admission remain unchanged. Full-domain retained and peak memory,
preparation latency, and prepared CPU/CUDA latency all improve while crossover stays
1/1. The tiny-batch overhead remains explicit. Broader projected strategies require
the same exact subset, identity, membership, evidence, and admission proofs and are

the next architectural boundary rather than an implicit generalization.
