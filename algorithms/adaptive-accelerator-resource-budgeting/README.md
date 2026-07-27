# Adaptive accelerator resource budgeting

This directory is the executable mirror for research ID
`adaptive-accelerator-resource-budgeting`. The human research record uses the
same ID under `docs/research/algorithms/`, and its mathematical contract, when
present, uses the same ID under `math/algorithms/`.

Implementations in Rust, C, CUDA, Python, or another justified language live
together here because the algorithm, not the language, owns the research.
Regenerable results belong in `out/` and remain Git ignored.

The active implementation intentionally remains product-owned by
`accelerator/resource_budget.py`; this research mirror owns experiment identity
and configuration rather than a duplicate scheduler. Reproducible capacity/live
resource output is emitted by `benchmarks/accelerator/resource_budget_measure.py`.
Synthetic scenarios are labeled explicitly and must never be reported as measured
hardware throughput.
