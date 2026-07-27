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
