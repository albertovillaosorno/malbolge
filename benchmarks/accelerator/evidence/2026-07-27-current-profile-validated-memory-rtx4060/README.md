# Validated current-profile memory evidence

This directory retains the RTX 4060 performance matrix after introducing
`ProfileMemoryImage`, an owned geometry-bound input representation that validates
and copies a profile memory image once and can reuse that proof across later
requests. Mutable `array('I')` inputs keep the original full per-call validation.

The benchmark constructs the validated image before the timed adapter calls. This
matches the intended lifecycle: loading/compilation pays one validation+ownership
cost, while repeated execution reuses the immutable-by-contract image.

## Provenance

- source commit: `2832279b2cb7d7ea7617648f4a4b0d9a2f4e2924`
- comparison baseline:
  `benchmarks/accelerator/evidence/2026-07-27-current-profile-resident-session-rtx4060/`
- platform: Windows x86-64
- Python: 3.14.6, repository-pinned wrapper
- CUDA: 13.3 Update 1, repository-pinned redistributables
- NVIDIA driver: 610.47
- device: NVIDIA GeForce RTX 4060 (`sm_89`)
- complete memory per VM: 4,782,969 words / 19,131,876 bytes
- complete-run workload: 64 committed no-op transitions per VM
- complete-run samples: 15 per batch size for 1/2/4/8/16/32
- phase samples: 15 per batch size for 1/8/32
- resident-session samples: 15 timed 64-step `advance()` calls per batch size for
  1/8/32/128
- `throughput.json` SHA-256:
  `011bf7dc485ffa92cdee41bef65af349876bff8b0ef1a8cab0804a541f8c871f`
- `phases.json` SHA-256:
  `2e5f61c7e828691d3a104263e23a6181d093405380e938c35a5d9381f5f8af01`
- `session.json` SHA-256:
  `f6faab80e7c23a3a79bd7fd75886b7997521df11a570360b7b84e9e9a3504e8a`

## Complete-snapshot result

| Batch | Previous VMs/s | Validated-image VMs/s | Median wall-time ratio |
| ---: | ---: | ---: | ---: |
| 1 | 10.878 | 41.577 | 3.822x |
| 2 | 18.353 | 48.769 | 2.657x |
| 4 | 27.908 | 51.792 | 1.856x |
| 8 | 37.380 | 53.166 | 1.422x |
| 16 | 45.826 | 54.755 | 1.195x |
| 32 | 51.668 | 55.395 | 1.072x |

The gain is largest for small batches because validation was an approximately
batch-invariant scan of one shared 4,782,969-word image. At batch 32, larger
snapshot construction/download/materialization costs already dominate.

## Phase attribution

Median validation+planning falls from 61.785 ms to 0.096 ms at batch 1, about
643x, and from 62.397 ms to 0.234 ms at batch 32, about 266x. The complete
profiled batch-1 wall time falls from 90.477 ms to 23.142 ms, about 3.91x.
Batch-32 profiled wall time falls from 583.100 ms to 543.110 ms, about 1.074x.

At batch 32 the remaining median phases are approximately:

- host batch construction: 203.743 ms
- upload: 20.653 ms
- kernel+sync: 0.092 ms
- download: 94.309 ms
- complete result decode/materialization: 180.691 ms

The next measured complete-snapshot boundary is therefore not validation. It is
host snapshot construction plus downloading into a packed temporary buffer and
copying each VM again into its final `array('I')` result.

## Resident-session check

The resident-session result remains in the same range: batch 128 records a
62,100 ns median `advance()`, about 2.061 million 64-step VM segments/s or
131.9 million VM-steps/s. Setup, observation, and snapshots remain outside this
timed region. This is not a complete-run or CPU-relative speedup claim.

## Interpretation boundary

`ProfileMemoryImage` does not weaken validation. Its constructor validates the
complete source and owns an isolated copy; its public word view is read-only and
it is bound to the validated geometry. A mutable array request still receives the
full existing validation path. The retained performance result therefore measures
proof reuse, not skipped correctness checks on mutable input.
