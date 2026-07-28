# In-place packed rotate-target batch-builder evidence

This bundle retains protocol version 6 and its immediate version-5 baseline. The
active builder reuses the first-representative array as final logical-index storage,
rotates it through overlapping native-word memoryviews plus only the wrapped prefix,
truncates by budget, freezes index bytes, releases mutable storage, and then creates
payload bytes.

## Provenance

- implementation commit: `4cb61a7b9e58fb147e3b1646df9f001069b3cb06`
- immediate baseline source commit: `fef2558600b2449892b8d68e4d95f19e869fc55a`
- raw observations: `raw.csv` (1,980 rows)
- aggregate workload SHA-256: `4448fd7594a50646c5da2ccea28b239fb80da4b16a005739f33db56ce5aa3777`
- `raw.csv` SHA-256: `ca31761b181d6e340f267c09f99fee07e6e896b6fd000ef536790853f045c8b2`
- `crossover.json` SHA-256: `eceeabb59455857bd062b9ad10b1c836f97e8d43fc455e215793a14e196347e5`
- `throughput.json` SHA-256: `6a8df4f0dc298c6edddc70fc76e332dfe8d808cdd97fa8a24ba6bc1dffffd216`
- `phases.json` SHA-256: `9369833f9d37c7f37c712ad290cbf75169d02a5e45b3959d19eedd7cda498a4c`
- `baseline-crossover.json` SHA-256: `1ede2cfa62ac8f2c24e7ca97e79c7bf1be72503f31c985079b54ae77a7bf6aaa`
- `baseline-throughput.json` SHA-256: `932d95ecff8dd5cd999049825de5927d2d89d2ef69532d72e263a4fcce254a6e`
- `baseline-phases.json` SHA-256: `6397f1b08faecc0f38000746b79366bf3faaacd49a62604c9c34109465a0f943`

## Environment

- host: Microsoft Windows 10.0.26200 x86-64
- Python: 3.14.6, repository-pinned installation
- CUDA: 13.3 Update 1
- NVIDIA driver: 610.47
- device: NVIDIA GeForce RTX 4060 (`sm_89`, 8,188 MiB)

## Proofs

- builder: `classic-u32le-bitset-inplace-first-representatives-v2`
- prepared reference: `cpu-scalar-packed-equality-v2`
- prepared input: `proof-bound-u32le-primitive-input-v1`
- candidate storage: `u32-index-fixed-width-payloads-rotation-v1`
- membership: `u32-rotation-or-pair-or-reference-binary-search-v1`
- ordinary validator: `u32le-broadword-domain-v1`
- CPU session: 1 build, 16 evaluations, 15 reuses, 59,049 resident words, rotate kind, and 59,049 table entries
- CUDA session: 1 build, 16 evaluations, 15 reuses, 16 packed evaluations, 59,049 resident words, and rotate kind
- first-representative, seed/budget, strict-rotation, exact proposal, independent admission, and malformed/forged/fabricated failures remain required

## Full-domain preparation and memory

| Metric | In-place v6 | Builder v5 | Change |
| --- | ---: | ---: | ---: |
| cold preparation | 64.606 ms | 76.130 ms | 1.178x |
| warm preparation | 65.101 ms | 76.584 ms | 1.176x |
| retained state | 710,647 B | 710,647 B | unchanged |
| peak allocation | 962,052 B (0.917 MiB) | 1,183,023 B (1.128 MiB) | **18.679% lower** |

Full-domain cold/warm crossover remains **1/1**.

## Throughput controls

| Route | In-place v6 | Baseline v5 | Ratio |
| --- | ---: | ---: | ---: |
| CPU ordinary | 79.943 ms | 90.869 ms | 1.137x |
| CPU prepared | 3.267 ms | 3.108 ms | 0.952x |
| CUDA ordinary | 92.133 ms | 103.562 ms | 1.124x |
| CUDA prepared | 0.385 ms | 0.479 ms | 1.245x |

The builder is timed in ordinary routes and outside prepared reuse intervals. CPU
and CUDA ordinary improve 1.137x and
1.124x. Prepared controls move in opposite
directions: CPU throughput is 0.952x, CUDA
throughput is 1.245x, and separate CPU/CUDA phase
totals are 0.996x/
0.983x. No prepared-execution effect is
attributed to the builder.

## Scale boundary

One-candidate peak is unchanged at 8,391 bytes and crossover remains 7/6. At 64
candidates, peak falls 8,788 to 8,635 bytes but ordinary timing varies upward in the
sub-millisecond regime. At 1,024 candidates, peak falls 22,155 to 19,116 bytes and
ordinary CUDA improves. Promotion is for deterministic scale preparation, not a
claim about every tiny timing sample.

## Component boundary

After v6, the batch-builder phase peaks near 710,190 bytes while retaining 473,546
bytes. The overall preparation peak near 962 KiB now occurs when the retained batch
coexists with candidate-state creation (~237 KiB incremental) or selector creation
(~253 KiB incremental). The next measured boundary is that post-builder coexistence,
not further representative-array compaction.

## Decision

The in-place packed builder is promoted. It preserves every exact proof and session
counter, reduces full-domain peak by 18.679%, improves cold/warm preparation by
1.178x/1.176x, improves ordinary CPU/CUDA routes, and leaves crossover unchanged at
every retained scale. Prepared-route variation remains an explicit contextual control.
