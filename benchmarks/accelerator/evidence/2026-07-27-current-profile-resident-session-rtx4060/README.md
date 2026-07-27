# Current-profile shared initialization and resident-session evidence

This directory retains the post-optimization RTX 4060 matrix for scalable
14-trit CUDA execution. It covers two distinct boundaries:

1. complete end-to-end `evaluate()` calls that still materialize every final
   4,782,969-word state; and
2. repeated `CudaProfileRunSession.advance()` calls whose complete VM state stays
   resident in device memory between bounded segments.

The implementation derives current memory width from `3**14`; the accelerator
backend still has no architecture-level 4,782,969-word ceiling.

## Provenance

- source commit: `ca787ac45ed70c28ad16cd0b1252f0cc02d2604b`
- comparison baseline:
  `benchmarks/accelerator/evidence/2026-07-27-current-profile-throughput-rtx4060/`
- platform: Windows x86-64
- Python: 3.14.6, repository-pinned wrapper
- CUDA: 13.3 Update 1, repository-pinned redistributables
- NVIDIA driver: 610.47
- device: NVIDIA GeForce RTX 4060 (`sm_89`)
- device memory snapshot: 8,585,084,928 total bytes; 7,449,083,904 free bytes
- complete memory per VM: 4,782,969 words / 19,131,876 bytes
- complete-run workload: 64 committed no-op transitions per VM
- complete-run samples: 15 per batch size for 1/2/4/8/16/32
- complete phase samples: 15 per batch size for 1/8/32
- resident-session workload: fifteen consecutive 64-step segments after one
  setup, with 960 no-op cells prepared in advance
- resident-session samples: 15 timed `advance()` calls per batch size for
  1/8/32/128
- `throughput.json` SHA-256:
  `2a79dddbb59f4011dc27e30bfe6df4910187fa3c10c940c11bc8a4607ab135e0`
- `phases.json` SHA-256:
  `8c39e7b579ba8395d7643aab0ec9638c5eee4dcd63da0ec446805b4a3a764b2c`
- `session.json` SHA-256:
  `c1661c529ca6c554c8787f7077438db4caa63dafcc8e6bd5f79d6112e42b81a8`

Commands:

```powershell
.dependencies/python/3.14.6/Scripts/python-jig.cmd `
  -m benchmarks.accelerator.profile_run_throughput

.dependencies/python/3.14.6/Scripts/python-jig.cmd `
  -m benchmarks.accelerator.profile_run_phase_profile

.dependencies/python/3.14.6/Scripts/python-jig.cmd `
  -m benchmarks.accelerator.profile_resident_session_throughput
```

## Complete-snapshot result

Shared initial memory is now copied from host once and replicated into private
per-VM device regions with device-to-device copies. The ordinary `evaluate()`
path still allocates a fully materialized host receive buffer because it knows a
complete snapshot is required immediately.

| Batch | Baseline VMs/s | Post-change VMs/s | Median wall-time ratio |
| ---: | ---: | ---: | ---: |
| 1 | 11.046 | 10.878 | 0.985x |
| 2 | 17.840 | 18.353 | 1.029x |
| 4 | 26.062 | 27.908 | 1.071x |
| 8 | 33.535 | 37.380 | 1.115x |
| 16 | 39.661 | 45.826 | 1.155x |
| 32 | 40.077 | 51.668 | 1.289x |

The optimization is therefore batch-sensitive rather than universal. Batch 1
shows no retained improvement, while larger shared-memory batches increasingly
benefit from avoiding repeated host-to-device copies.

At batch 32, median upload time falls from 147.700 ms to 21.307 ms, about 6.93x.
Median profiled total time falls from 710.273 ms to 583.100 ms, about 1.218x.
Validation/planning, host materialization, download, and complete result decode
remain essentially unchanged, so they now account for most of the complete-run
wall time.

## Resident-session result

The resident session uses a lazy host snapshot mapping and keeps complete mutable
VM state in private device regions across launches. Only the scalar state buffer
is downloaded by `observe()`. Full memory/output transfer occurs only when the
caller explicitly requests `snapshot()`.

| Batch | Median `advance()` ns | VM segments/s | VM steps/s |
| ---: | ---: | ---: | ---: |
| 1 | 47,400 | 21,097 | 1,350,211 |
| 8 | 59,500 | 134,454 | 8,605,042 |
| 32 | 55,700 | 574,506 | 36,768,402 |
| 128 | 63,900 | 2,003,130 | 128,200,313 |

These are **steady-resident launch rates**, not complete-run throughput. Session
setup, initial validation/allocation/upload, compact observation, and any full
snapshot are deliberately outside the timed `advance()` region. The values must
not be compared directly with complete `evaluate()` VMs/s or presented as a
CPU-relative application speedup.

## Interpretation boundary

The evidence confirms the earlier phase diagnosis: semantic kernel execution was
already cheap, and state movement dominated short complete snapshots. Device-side
replication improves large homogeneous complete batches, while resident sessions
remove repeated full-state host/device movement entirely between continuation
segments. Remaining measured opportunities include avoiding repeated full-domain
validation for safely reusable immutable inputs and reducing complete snapshot
materialization when callers do require host memory.

This remains one RTX 4060 development result. Broader hardware evidence and any
CPU-relative or application-level speedup claim require separate measurements.
