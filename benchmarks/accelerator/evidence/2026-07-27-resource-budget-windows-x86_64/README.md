# Adaptive accelerator resource-budget evidence

This directory retains post-commit resource-planning evidence for
`adaptive-accelerator-resource-budgeting`.

## Provenance

- source commit: `288b321b3af89e63f2702965567adfb93b8abf83`
- platform: Windows x86-64
- Python: 3.14.6, repository-pinned wrapper
- CUDA: 13.3 Update 1, repository-pinned redistributables
- NVIDIA driver: 610.47
- device: NVIDIA GeForce RTX 4060
- compute capability: 8.9 / `sm_89`
- reported physical memory: 8,188 MiB (`nvidia-smi`)
- `resource-plan.json` SHA-256:
  `e28c00783db6c8503e30bd7fa492dc1974dd9455076a4e93c3242e426dba7d63`

## Command

```powershell
.dependencies/python/3.14.6/Scripts/python-jig.cmd `
  -m benchmarks.accelerator.resource_budget_measure --cuda
```

## Observations

The live Driver API snapshot recorded 8,585,084,928 total bytes and
7,451,181,056 free bytes, 24 multiprocessors, and 1,024 maximum threads per
block. The deterministic reserve was 536,567,808 bytes, leaving 6,914,613,248
budgeted bytes for resident state.

The current-profile capacity row is a **layout model**, not current-profile GPU
execution: a modeled 19,131,940-byte resident state admits 361 items in the
first live-device chunk. The classic row contains only 10,000 requested scenario
items, so its 10,000-item first chunk means "at least 10,000 fit" rather than an
uncensored maximum.

The 128 MiB and 80 GiB rows are explicitly synthetic planning scenarios. Under
the same current-state byte model and reserve rule they admit 6 and 4,209 items
respectively in the first chunk. They demonstrate that the planner has no fixed
development-GPU batch ceiling; they do not demonstrate performance on hardware
that was not present.

## Limits

This evidence measures resource discovery and deterministic capacity planning
only. It does not establish throughput, transfer overlap, current-profile CUDA
correctness, or behavior on a physical 128 MiB/80 GiB accelerator. Those remain
separate acceptance obligations.
