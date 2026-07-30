# Adaptive accelerator resource budgeting

This directory is the executable mirror for research ID
`adaptive-accelerator-resource-budgeting`. The human research record uses the
same ID under `docs/research/algorithms/`, and its mathematical contract, when
present, uses the same ID under `math/algorithms/`.

Implementations in Rust, C, CUDA, Python, or another justified language live
together here because the algorithm, not the language, owns the research.
Regenerable results belong in `out/` and remain Git ignored.

The active implementations intentionally remain product-owned by
`accelerator/resource_budget.py`, `accelerator/ticket_admission.py`, and the exact
CUDA registry/loader/executor under `accelerator/cuda/`; this research mirror owns
experiment identity and configuration rather than duplicate schedulers.
Reproducible capacity/live resource output is emitted by
`benchmarks/accelerator/resource_budget_measure.py`. The ticket profile generator at
`benchmarks/accelerator/ticket_admission_profile_manifest.py` converts retained
route evidence into canonical product JSON, while runtime code reads only that
tracked manifest. Synthetic scenarios are labeled explicitly and must never be
reported as measured hardware throughput.
