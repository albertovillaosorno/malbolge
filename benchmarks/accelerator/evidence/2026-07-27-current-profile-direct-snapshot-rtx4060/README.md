# Direct current-profile snapshot evidence

This directory retains the RTX 4060 matrix after removing the redundant packed
host memory snapshot from scalable CUDA result materialization. Complete memory
is downloaded directly into each final `array('I')` returned by
`ProfileRunResult`; no second full-memory slice/copy is required.

A singleton request reuses its privately owned upload buffer as the final result
array. Caller-owned mutable input is never used as the download target, so the
optimization preserves the no-alias input contract.

## Provenance

- source commit: `f25f4563fbed94508450793893f319f5001fcfe9`
- comparison baseline:
  `benchmarks/accelerator/evidence/2026-07-27-current-profile-validated-memory-rtx4060/`
- platform: Windows x86-64
- Python: 3.14.6, repository-pinned wrapper
- CUDA: 13.3 Update 1, repository-pinned redistributables
- NVIDIA driver: 610.47
- device: NVIDIA GeForce RTX 4060 (`sm_89`)
- complete memory per VM: 4,782,969 words /
  19,131,876 bytes
- complete-run samples: 15 per batch size for
  1,2,4,8,16,32
- phase samples: 15 per batch size for 1/8/32
- resident-session samples: 15 timed `advance()` calls per batch
  size for 1,8,32,128
- `throughput.json` SHA-256: `5e1c99e27ed4753f5a86e998f4640b974da269c6a1d7728a466ce8702963e3df`
- `phases.json` SHA-256: `dfb518ed884c1aeac499d693cd86c562d55ff785f3a584b9efc0f873221e2db3`
- `session.json` SHA-256: `2649f92d41ed5d205e5d4e9ff81c65422b40bff03df4b624d390032fb522a346`

## Complete-snapshot result

| Batch | Previous VMs/s | Direct-snapshot VMs/s | Median wall-time ratio |
| ---: | ---: | ---: | ---: |
| 1 | 41.577 | 60.426 | 1.453x |
| 2 | 48.769 | 58.865 | 1.207x |
| 4 | 51.792 | 71.912 | 1.388x |
| 8 | 53.166 | 82.115 | 1.545x |
| 16 | 54.755 | 89.032 | 1.626x |
| 32 | 55.395 | 93.680 | 1.691x |

At batch 32, complete-snapshot throughput rises from
55.395 to
93.680 VMs/s, a
1.691x median wall-time improvement over
the validated-memory baseline. Batch 1 also rises from
41.577 to
60.426 VMs/s because the singleton path reuses
one private owned buffer as both upload source and final snapshot target.

## Batch-32 phase attribution

| Phase | Previous ms | Direct-snapshot ms | Previous/current |
| --- | ---: | ---: | ---: |
| Validation + planning | 0.234 | 0.208 | 1.128x |
| Host batch build | 203.743 | 13.391 | 15.215x |
| Allocate | 1.823 | 1.969 | 0.926x |
| Upload | 20.652 | 21.986 | 0.939x |
| Kernel + sync | 0.092 | 0.091 | 1.012x |
| Download | 94.309 | 97.970 | 0.963x |
| Result materialization | 180.691 | 163.335 | 1.106x |
| Release | 4.715 | 4.841 | 0.974x |

Median host batch construction falls from
203.743 ms to
13.391 ms. Result materialization falls from
180.691 ms to
163.335 ms. The D-to-H phase remains the necessary
full snapshot transfer into final arrays rather than a transfer into a redundant
intermediate packed buffer.

## Resident-session check

| Batch | Median `advance()` ns | VM segments/s | VM steps/s |
| ---: | ---: | ---: | ---: |
| 1 | 46,300 | 21598 | 1382289 |
| 8 | 60,400 | 132450 | 8476821 |
| 32 | 60,600 | 528053 | 33795380 |
| 128 | 63,100 | 2028526 | 129825674 |

Resident-session values remain steady-state launch measurements only. Setup,
compact observation, and optional snapshots are outside the timed `advance()`
region and must not be compared directly with complete-run throughput.

## Interpretation boundary

This optimization removes avoidable host storage and copying; it does not make a
requested complete snapshot free. A caller that asks for all 4,782,969
words still incurs final array allocation/page commitment plus device-to-host
transfer. Persistent sessions remain the path for workloads that can continue
without materializing complete state after every bounded segment.

This is one RTX 4060 development result, not a CPU-relative or cross-device
speedup claim.
