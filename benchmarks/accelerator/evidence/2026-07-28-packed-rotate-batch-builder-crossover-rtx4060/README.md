# Packed rotate-target batch-builder crossover evidence

This bundle retains protocol version 5 and the immediate version-4 baseline. The
active builder scans encoded candidate words, records stable first representatives
with a classic-domain bitset, rotates packed u32 indexes by seed and budget, and
emits payload bytes without decoded candidate tuples or generic dictionary pruning.
The trusted prepared reference uses independent scalar CPU formulas over packed input.

## Provenance

- implementation commit: `fef2558600b2449892b8d68e4d95f19e869fc55a`
- immediate baseline source commit: `1deca088aca6f3a1aa862833bdbbcfb167b1a121`
- raw observations: `raw.csv` (1,980 rows)
- aggregate workload SHA-256: `4448fd7594a50646c5da2ccea28b239fb80da4b16a005739f33db56ce5aa3777`
- `raw.csv` SHA-256: `1e2c520b8d16b693d288a9492654c8253998148e4a84333aa7a05550a2407e8e`
- `crossover.json` SHA-256: `1ede2cfa62ac8f2c24e7ca97e79c7bf1be72503f31c985079b54ae77a7bf6aaa`
- `throughput.json` SHA-256: `932d95ecff8dd5cd999049825de5927d2d89d2ef69532d72e263a4fcce254a6e`
- `phases.json` SHA-256: `6397f1b08faecc0f38000746b79366bf3faaacd49a62604c9c34109465a0f943`
- `baseline-crossover.json` SHA-256: `613e6777e5efedda24714a9e420c2b6773b4825189d3f0ffb5f623dc1929a223`
- `baseline-throughput.json` SHA-256: `90ddaf40e24abebfc723c0c6cba433cfe8f7990e9eb4b6b71a6423a685f6c138`
- `baseline-phases.json` SHA-256: `8b266ad49cba889d111424dd02287793b75b240b8882171c4ed61046f20411b7`

## Environment

- host: Microsoft Windows 10.0.26200 x86-64
- Python: 3.14.6, repository-pinned installation
- CUDA: 13.3 Update 1
- NVIDIA driver: 610.47
- device: NVIDIA GeForce RTX 4060 (`sm_89`, 8,188 MiB)

## Proofs

- builder: `classic-u32le-bitset-first-representatives-v1`
- prepared reference: `cpu-scalar-packed-equality-v2`
- prepared input: `proof-bound-u32le-primitive-input-v1`
- candidate storage: `u32-index-fixed-width-payloads-rotation-v1`
- membership: `u32-rotation-or-pair-or-reference-binary-search-v1`
- ordinary validator: `u32le-broadword-domain-v1`
- CPU session: 1 build, 16 evaluations, 15 reuses, 59,049 resident words, rotate kind, and 59,049 table entries
- CUDA session: 1 build, 16 evaluations, 15 reuses, 16 packed evaluations, 59,049 resident words, and rotate kind
- exact proposal, independent trusted admission, reference/membership/selector counts, and malformed/forged/fabricated failures remain required

## Full-domain preparation and memory

| Metric | Builder v5 | Packed-input v4 | Change |
| --- | ---: | ---: | ---: |
| cold preparation | 76.130 ms | 122.990 ms | 1.616x |
| warm preparation | 76.584 ms | 109.027 ms | 1.424x |
| retained state | 710,647 B | 713,791 B | 0.440% lower |
| peak allocation | 1,183,023 B (1.128 MiB) | 8,802,328 B (8.395 MiB) | **86.560% lower** |

Full-domain cold/warm crossover remains **1/1**.

## Throughput controls

| Route | Builder v5 | Baseline v4 | Ratio |
| --- | ---: | ---: | ---: |
| CPU ordinary | 90.869 ms | 132.848 ms | 1.462x |
| CPU prepared | 3.108 ms | 3.261 ms | 1.049x |
| CUDA ordinary | 103.562 ms | 144.440 ms | 1.395x |
| CUDA prepared | 0.479 ms | 0.429 ms | 0.896x |

The builder is inside ordinary routes and outside prepared reuse intervals. CPU and
CUDA ordinary improve 1.462x and
1.395x. CUDA prepared throughput is the retained
negative control at 0.896x; the separate CUDA
phase total is 0.992x, so no causal prepared-
execution speedup or regression is attributed to the builder.

## Scale boundary

The fixed classic-domain bitset raises one-candidate peak from 2,664 to 8,391 bytes.
At 64 candidates, peak is 8,788 versus 6,016 bytes and warm crossover moves from
3 to 4 runs. At 1,024 candidates, peak falls from 129,344 to 22,155 bytes, while at
59,049 it falls 86.560%. Promotion is therefore for large deterministic batches,
not universal small-batch memory or amortization.

## Decision

The packed builder and scalar packed reference are promoted for rotate-target search.
They preserve all exact proof/admission boundaries, reduce full-domain peak by 86.560%,
improve cold/warm preparation by 1.616x/1.424x, improve ordinary CPU/CUDA routes,
and retain one-run full-domain crossover. Small-scale fixed-bitset overhead and the
prepared CUDA contextual-control variation remain explicit negative results.
