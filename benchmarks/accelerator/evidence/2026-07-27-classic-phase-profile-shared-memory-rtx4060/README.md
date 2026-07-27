# Shared immutable resident-memory phase evidence

This directory retains the post-commit phase matrix after adding intra-batch
shared-memory identity validation and a compact all-shared-memory host-image fast
path. No cross-call cache or hidden retained state is used.

## Provenance

- source commit: `4ec8b37203dc041737a2c6bfbfbc25718744e243`
- comparison commit: `d804052`
- original phase baseline: `9ed6e9b994392be4c8e75d9783baded80da50dbf`
- platform: Windows x86-64
- Python: 3.14.6, repository-pinned wrapper
- CUDA: 13.3 Update 1, repository-pinned redistributables
- NVIDIA driver: 610.47
- device: NVIDIA GeForce RTX 4060 (`sm_89`)
- samples: 15 per batch size
- workload: 64 committed no-op transitions per classic VM
- `phases.json` SHA-256: `9367ed4bdd5d99681917e02511172e8dce5b3ac40d1eb6f3092a849e81f415e9`

## Comparison

| Batch | Prior median ns | Shared-memory median ns | Speedup | VMs/s |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 4,856,600 | 3,808,600 | 1.28x | 262.56 |
| 8 | 36,729,100 | 9,807,800 | 3.74x | 815.68 |
| 32 | 148,679,800 | 30,978,600 | 4.80x | 1032.97 |
| 128 | 636,002,300 | 118,917,500 | 5.35x | 1076.38 |

Batch 128 falls from 636,002,300 ns to 118,917,500 ns
(5.35x faster) and reaches
1076.38 VMs/s. Relative to the original phase baseline,
that is 39.51x lower wall time.

At batch 128, validation/planning is 1,681,800 ns and
host construction 10,613,600 ns. Decode now dominates at
89,294,200 ns, about
75.09% of total wall time, while the
kernel remains only 0.1039%.

This result promotes batch-local shared immutable memory reuse. The next measured
boundary is no longer GPU execution or host input preparation; it is materializing
complete 59,049-word final memories back into Python tuples. A truly resident API
should therefore permit continued execution and compact outcome inspection before
requiring a full host snapshot.
