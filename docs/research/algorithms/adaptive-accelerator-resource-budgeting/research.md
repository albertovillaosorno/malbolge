# Adaptive accelerator resource budgeting

## Status

Active

## Research Question

Does `adaptive-accelerator-resource-budgeting` provide a reproducible verified
benefit over its declared baseline for the Malbolge compiler or execution
problem without weakening semantic correctness?

## Background

Discover available memory and compute resources at runtime and choose batch
size, state layout, caches, and search breadth accordingly. Tiny devices around
Small-memory devices must remain usable while additional addressable
resources on arbitrarily larger devices must increase available work rather than
hitting a fixed artificial VRAM ceiling. The 128 MiB and 80 GiB values are only
example probe points, not supported-range endpoints.

- Status: Active
- Research ID: `adaptive-accelerator-resource-budgeting`
- Last reviewed: 2026-07-26

## Prior Work

- `../../../bibliography/platforms-and-runtimes/accelerators/nvidia-cuda.md`

## Hypothesis

- Baseline: one fixed resident batch ceiling chosen for a development GPU. Such
  a ceiling either wastes larger devices or fails when a smaller device cannot
  admit the configured state set.
- H1: measuring free/total memory and coarse compute capacity at runtime, then
  greedily partitioning exact per-item byte requirements below an explicit
  reserve, admits the same workload across wider device sizes without changing
  semantic acceptance.
- H0/rejection condition: reject the planner if one admitted chunk exceeds its
  measured usable bytes, if an item that cannot fit alone is admitted, if input
  order changes, or if increasing otherwise-equivalent usable memory reduces
  resident breadth. Performance benefit remains unproven until raw throughput
  samples exist.

## Method

The research identity and configuration live at
`algorithms/adaptive-accelerator-resource-budgeting/`. The product planner lives
in `accelerator/resource_budget.py`; the reproducible measurement entry point is
`benchmarks/accelerator/resource_budget_measure.py`. The experiment deliberately
separates synthetic capacity scenarios from live CUDA resource evidence. Raw
regenerable output stays outside correctness authority.

## Evidence

Candidate generation, heuristics, models, and accelerators are untrusted. A
research result can compare quality or cost only after the trusted semantic
verifier accepts the candidate under the declared target profile.

- The scheduler runs within measured memory limits from approximately 128 MiB
  through large-memory accelerators and converts additional resources into
  measured throughput/search breadth without fixed-size assumptions.
- A CPU/reference path remains sufficient for correctness, and accelerator
  failure/unavailability changes performance rather than semantic acceptance.
- The work states a falsifiable question or hypothesis, an explicit baseline,
  and an observation that would reject or materially weaken the proposed
  technique before performance conclusions are accepted.
- If executable algorithm research is required, the stable ID is mirrored under
  `docs/research/algorithms/<id>/` and `algorithms/<id>/`; ordinary product
  engineering is not forced into that mirror.
- Performance conclusions use equivalent workloads and report raw-sample
  provenance, resource budgets, dispersion/uncertainty, and failure/success
  behavior rather than only a best-case number.

## Results

The first correctness slice is active. `AcceleratorResources` validates measured
free/total memory, maximum threads per block, and multiprocessor count.
`plan_resident_batches` reserves the larger of 8 MiB or one sixteenth of total
memory, then constructs maximal contiguous input-order chunks whose exact
resident byte requirement fits the remaining free-memory budget. An item that
cannot fit alone is rejected before backend allocation.

The classic resident CUDA adapter now uses this plan before allocation. CUDA
resource evidence comes from `cuMemGetInfo_v2` plus
`cuDeviceGetAttribute`; no GPU model name selects a batch limit. Synthetic
boundary tests model a 19,131,940-byte current-profile state and admit six such
states in the first chunk of a 128 MiB device model versus 4,209 in an 80 GiB
model under the same reserve rule. These are capacity-model results, **not**
claims that either hardware class was physically benchmarked.

Existing RTX 4060 classic resident differential tests continue to pass after the
planner is inserted into the real allocation path. Post-commit resource evidence
at `benchmarks/accelerator/evidence/2026-07-27-resource-budget-windows-x86_64/`
records commit/toolchain/device identity plus the raw planning JSON. The live
snapshot reports 8,585,084,928 total bytes, 7,451,181,056 free bytes, 24 SMs,
and 1,024 maximum threads/block; the modeled current state admits 361 items in
the first chunk. This remains capacity evidence, not throughput. Post-commit
no-ceiling evidence under
`benchmarks/accelerator/evidence/2026-07-27-unbounded-vram-windows-x86_64/`
adds a 100,000 GiB synthetic scenario with 100,000 classic items. The complete
workload is admitted as 72,736 + 27,264 items because classic CUDA splits at its
32-bit per-launch memory-index boundary rather than imposing a VRAM maximum.

The first retained throughput matrix at
`benchmarks/accelerator/evidence/2026-07-27-classic-throughput-rtx4060/` is a
negative scaling result. For an exact 64-step classic no-op workload, median
end-to-end throughput is 29.127 VMs/s at batch 1, 28.136 at batch 8, 27.922 at
batch 32, and 27.751 at batch 128. Batch 128 is about 4.73% slower than batch 1.
Therefore larger resident batches are not yet converting capacity into measured
throughput. The evidence does not assign causality; phase-separated timing is the
next experiment.

Phase-separated post-commit evidence under
`benchmarks/accelerator/evidence/2026-07-27-classic-phase-profile-rtx4060/`
locates that failure. At batch 128, median kernel+sync time is 458,100 ns out of
4,698,614,500 ns total (about 0.0097%). Validation/planning, host-buffer
construction, and result decode account for about 97.75% combined. The evidence
therefore rejects CUDA-kernel tuning as the next bottleneck-directed action and
selects host representation/validation work for optimization first.

The first bottleneck-directed optimization is retained under
`benchmarks/accelerator/evidence/2026-07-27-classic-phase-profile-array-rtx4060/`.
Removing duplicate request validation and replacing tuple/ctypes flattening with
contiguous unsigned-word buffers reduces batch-8 median wall time from
287,277,100 ns to 66,098,600 ns (4.35x) and batch-128 time from 4,698,614,500 ns
to 1,162,925,900 ns (4.04x). Batch-128 throughput rises from about 27.24 to
110.07 VMs/s. Validation/planning is now the dominant measured phase, so the next
candidate is safe reuse of validation for immutable requests.

## Threats to Validity

Initial threats include challenge-family bias, hardware/toolchain sensitivity,
search-seed variance, verifier bounds, and overfitting to small Malbolge blocks.
Each experiment must narrow these threats before drawing a conclusion.

## Conclusion

Accept the measured-memory planner as a correctness-preserving allocation guard
for resident classic CUDA execution. Do not yet conclude that it improves
throughput or completes adaptive search breadth: live retained measurements,
current-profile execution, and broader hardware evidence remain open.

## References

- [Replaceable Accelerator And Algorithm
  Ports](../../../technical/adr/replaceable-accelerator-and-algorithm-ports.md)
- [Verification Trust
  Boundary](../../../technical/adr/verification-trust-boundary.md)
- [Research Evidence And Algorithm
  Mirror](../../adr/research-evidence-and-algorithm-mirror.md)
