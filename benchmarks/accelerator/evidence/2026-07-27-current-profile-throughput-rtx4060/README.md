# Current-profile CUDA throughput and phase evidence

This directory retains the first post-commit performance matrix for complete
14-trit resident CUDA execution. The benchmark derives the memory width from
`3**14`; the backend does not embed the resulting 4,782,969-word size as an
architecture limit.

## Provenance

- source commit: `d280612dd979b5f9bf653c243d0b1df0a92be9fe`
- platform: Windows x86-64
- Python: 3.14.6, repository-pinned wrapper
- CUDA: 13.3 Update 1, repository-pinned redistributables
- NVIDIA driver: 610.47
- device: NVIDIA GeForce RTX 4060 (`sm_89`)
- workload: 64 committed no-op transitions per 14-trit profile VM
- complete memory per VM: 4,782,969 words / 19,131,876 bytes
- throughput samples: 15 per batch size for 1/2/4/8/16/32
- phase samples: 15 per batch size for 1/8/32
- `throughput.json` SHA-256:
  `8bab017e71885da66d2c7e39d4a1fd8048815eea009d2230a24f8437da473981`
- `phases.json` SHA-256:
  `2358599e653c30470a529892082521c91c012d4283800fd2ebef237cb9b26012`

Commands:

```powershell
.dependencies/python/3.14.6/Scripts/python-jig.cmd `
  -m benchmarks.accelerator.profile_run_throughput

.dependencies/python/3.14.6/Scripts/python-jig.cmd `
  -m benchmarks.accelerator.profile_run_phase_profile
```

## End-to-end result

The public adapter gains throughput as independent complete states are batched,
but the gain is nearly saturated by batch 16 on this workload and hardware.

| Batch | Median ns | Median VMs/s | Median VM-steps/s |
| ---: | ---: | ---: | ---: |
| 1 | 90,530,700 | 11.046 | 706.94 |
| 2 | 112,106,300 | 17.840 | 1,141.77 |
| 4 | 153,481,000 | 26.062 | 1,667.96 |
| 8 | 238,557,700 | 33.535 | 2,146.23 |
| 16 | 403,417,100 | 39.661 | 2,538.32 |
| 32 | 798,472,200 | 40.077 | 2,564.90 |

Batch 32 reaches about 3.63x the batch-1 VM throughput, but improves only about
1.05% over batch 16. A batch-32 complete memory image alone contains 612,220,032
bytes (about 583.86 MiB), before accounting for the other host/device buffers and
result objects used during one evaluation.

## Phase attribution

The phase run shows that semantic GPU execution is already negligible relative
to validating, copying, transferring, and materializing the full state.

| Phase | Batch 1 median ms | Batch 8 median ms | Batch 32 median ms | Batch 32 share |
| --- | ---: | ---: | ---: | ---: |
| Validation + planning | 61.483 | 61.664 | 62.165 | 8.75% |
| Host batch build | 11.917 | 49.577 | 178.530 | 25.14% |
| Allocate | 0.508 | 0.902 | 1.808 | 0.25% |
| Upload | 5.028 | 37.869 | 147.700 | 20.79% |
| Kernel + sync | 0.080 | 0.098 | 0.100 | 0.014% |
| Download | 3.115 | 23.702 | 94.175 | 13.26% |
| Full result decode | 5.536 | 44.826 | 182.020 | 25.63% |
| Release | 0.458 | 1.586 | 5.213 | 0.73% |

At batch 32, validation, host construction, upload, download, and full decode
account for about 93.57% of the measured phase wall time. The kernel accounts for
about 0.014%. The roughly 62 ms validation/planning cost is almost batch-invariant
here because all requests deliberately share one immutable benchmark memory
identity inside each call, so the contract scans that 4,782,969-word image once.

## Interpretation boundary

This is one RTX 4060 development result, not a cross-device speedup claim. It does
establish that larger VRAM capacity and larger batches are not the immediate
performance limit for this 64-step complete-snapshot workload. The selected next
optimization boundary is host-state handling: avoid repeated full-domain Python
validation when an already validated immutable representation can carry that
proof, and avoid forcing a complete host snapshot between resident continuation
segments when callers only need compact outcome inspection.
