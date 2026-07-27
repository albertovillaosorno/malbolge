# Contiguous resident-host-buffer phase evidence

This directory retains the first post-optimization phase matrix after removing
resident-request double validation and replacing tuple/ctypes host flattening
with contiguous `array('I')` owners plus zero-copy ctypes views.

## Provenance

- source commit: `e23ee0380f97568ad705a13afcf54106c656f5c5`
- comparison baseline: `9ed6e9b994392be4c8e75d9783baded80da50dbf`
- platform: Windows x86-64
- Python: 3.14.6, repository-pinned wrapper
- CUDA: 13.3 Update 1, repository-pinned redistributables
- NVIDIA driver: 610.47
- device: NVIDIA GeForce RTX 4060 (`sm_89`)
- samples: 15 per batch size
- workload: 64 committed no-op transitions per classic VM
- `phases.json` SHA-256: `3e7c676511ee0643dccb33ecd5973b32426795e63a8b8304f94b4cf6f58f260d`

## End-to-end comparison

| Batch | Baseline median ns | Optimized median ns | Speedup | Optimized VMs/s |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 32,951,200 | 8,189,000 | 4.02x | 122.12 |
| 8 | 287,277,100 | 66,098,600 | 4.35x | 121.03 |
| 32 | 1,143,321,000 | 275,697,500 | 4.15x | 116.07 |
| 128 | 4,698,614,500 | 1,162,925,900 | 4.04x | 110.07 |

At batch 8, median total time falls from 287,277,100 ns to
66,098,600 ns (4.35x faster).
Host-build median falls from 112,533,800 ns to
16,993,900 ns and decode from 88,993,900 ns to
4,973,300 ns.

At batch 128, throughput rises from 27.24 to
110.07 VMs/s while kernel+sync remains only
0.0400% of total time. The dominant
remaining phase is request validation/planning at
59.56%.

This evidence promotes contiguous host buffers and duplicate-validation removal
as measured improvements. It does not yet establish the best possible host path;
immutable-request validation reuse is the next bottleneck-directed candidate.
