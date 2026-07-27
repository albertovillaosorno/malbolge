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
