# Unbounded accelerator-memory planning evidence

This directory retains post-commit evidence for the no-artificial-VRAM-ceiling
resource planner.

## Provenance

- source commit: `2b29776bb2580d2fd03c0dadd2274cc2329f7205`
- platform: Windows x86-64
- Python: 3.14.6, repository-pinned wrapper
- CUDA: 13.3 Update 1, repository-pinned redistributables
- NVIDIA driver: 610.47
- live device: NVIDIA GeForce RTX 4060 (`sm_89`)
- `resource-plan.json` SHA-256: `2ad39138d5bfcce3b3e96bbf2e3572f22c2f13f234de362e4669a7f5f6a69573`

## Command

```powershell
.dependencies/python/3.14.6/Scripts/python-jig.cmd -m benchmarks.accelerator.resource_budget_measure --cuda
```

## Result

The planner has no configured upper VRAM bound. The 128 MiB and 80 GiB rows are
example capacity probes only. A separate synthetic 100,000 GiB scenario requests
100,000 classic resident items and admits the complete workload.

Classic CUDA currently uses 32-bit per-launch memory offsets. Therefore the huge
scenario is intentionally split at 72,736 items in the first launch and 27,264
in the second. That limit is a backend representation boundary, not a device
memory ceiling: additional addressable VRAM can still increase total resident
capacity and work is partitioned rather than rejected or truncated.

The live RTX 4060 rows remain capacity-model evidence. The current-profile row is
not current-profile CUDA execution, and no synthetic memory size is a hardware
throughput claim.
