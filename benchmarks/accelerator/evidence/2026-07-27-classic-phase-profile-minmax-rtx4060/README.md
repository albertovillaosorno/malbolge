# Aggregate resident-validation phase evidence

This directory retains the post-commit phase matrix after replacing Python
per-word validation loops with aggregate `min`/`max` checks over immutable
classic request tuples.

## Provenance

- source commit: `d804052404dcf6b254c20d3cf7ea59e635f5b658`
- comparison commit: `e23ee0380f97568ad705a13afcf54106c656f5c5`
- platform: Windows x86-64
- Python: 3.14.6, repository-pinned wrapper
- CUDA: 13.3 Update 1, repository-pinned redistributables
- NVIDIA driver: 610.47
- device: NVIDIA GeForce RTX 4060 (`sm_89`)
- samples: 15 per batch size
- workload: 64 committed no-op transitions per classic VM
- `phases.json` SHA-256: `2c1c0d7c89a7ac3fe8c78ac5ac046a37c62942746ff87371c6b1f1d7df4d69fb`

## Comparison

| Batch | Prior median ns | Aggregate-validation ns | Speedup | VMs/s |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 8,189,000 | 4,856,600 | 1.69x | 205.91 |
| 8 | 66,098,600 | 36,729,100 | 1.80x | 217.81 |
| 32 | 275,697,500 | 148,679,800 | 1.85x | 215.23 |
| 128 | 1,162,925,900 | 636,002,300 | 1.83x | 201.26 |

Batch 8 falls from 66,098,600 ns to 36,729,100 ns
(1.80x faster), with validation/planning
falling from 41,703,500 ns to
11,253,500 ns.

Relative to the original phase baseline, batch 128 falls from 4,698,614,500 ns
to 636,002,300 ns, a 7.39x wall-time
improvement, and reaches 201.26 VMs/s.

The dominant remaining phase is host-buffer construction. Repeated immutable
memory identities inside one batch are therefore the next candidate: they can be
validated and converted once per identity while preserving independent device
state for each VM.
