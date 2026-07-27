# Accelerator benchmark tooling

This directory owns reproducible accelerator measurement entry points and
retained evidence. It does not define VM correctness.

`resource_budget_measure.py` emits two explicitly synthetic capacity scenarios
and, with `--cuda`, one live CUDA resource snapshot plus classic/current resident
capacity plans. Synthetic rows are planning-model evidence only; they are never
hardware throughput claims.

Run from the repository root with the pinned Python wrapper:

```powershell
.dependencies/python/3.14.6/Scripts/python-jig.cmd `
  -m benchmarks.accelerator.resource_budget_measure --cuda
```

Retained evidence belongs under `benchmarks/accelerator/evidence/` with exact
commit/toolchain/device/command provenance.

`classic_run_throughput.py` measures 15 raw samples for batch sizes 1, 8, 32,
and 128. Each resident classic VM commits exactly 64 no-op transitions and must
finish by budget exhaustion; validation occurs outside the timed interval. This
is an end-to-end adapter measurement including host packing, transfer, kernel,
copy-back, and decode costs.

Run with:

```powershell
.dependencies/python/3.14.6/Scripts/python-jig.cmd `
  -m benchmarks.accelerator.classic_run_throughput
```

`classic_run_phase_profile.py` uses the adapter's diagnostic
`profile_evaluate()` path to retain wall-clock totals for validation/planning,
host batch construction, device allocation, upload, kernel+sync, download,
result decode, and release. The ordinary `evaluate()` path does not collect these
timings.

Run with:

```powershell
.dependencies/python/3.14.6/Scripts/python-jig.cmd `
  -m benchmarks.accelerator.classic_run_phase_profile
```

`profile_run_throughput.py` measures 15 end-to-end samples for batch sizes 1, 2,
4, 8, 16, and 32. The fixture derives current memory width from `3**14`; each VM
commits exactly 64 no-op transitions and materializes the complete 4,782,969-word
result. The timed region includes validation/planning, host assembly, allocation,
transfers, kernel execution, full result decode, and release.

Run with:

```powershell
.dependencies/python/3.14.6/Scripts/python-jig.cmd `
  -m benchmarks.accelerator.profile_run_throughput
```

`profile_run_phase_profile.py` measures the same current-profile workload with
adapter diagnostics split into validation/planning, host construction,
allocation, upload, kernel+sync, download, full result decode, and release. It
uses batch sizes 1, 8, and 32 with 15 samples each so phase evidence remains
comparable with the end-to-end throughput run without retaining redundant large
batch points.

Run with:

```powershell
.dependencies/python/3.14.6/Scripts/python-jig.cmd `
  -m benchmarks.accelerator.profile_run_phase_profile
```
