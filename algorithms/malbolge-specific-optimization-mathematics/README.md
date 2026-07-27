# Malbolge-specific optimization mathematics

This directory is the executable mirror for research ID
`malbolge-specific-optimization-mathematics`. The human research record uses the
same ID under `docs/research/algorithms/`, and its mathematical contract, when
present, uses the same ID under `math/algorithms/`.

Implementations in Rust, C, CUDA, Python, or another justified language live
together here because the algorithm, not the language, owns the research.
Regenerable results belong in `out/` and remain Git ignored.

The active first experiment studies exact CPU VM table/factorization reductions.
Its versioned configuration is `experiment.toml`; raw performance evidence lives
under `benchmarks/interpreter/evidence/2026-07-26-windows-x86_64/`, while
semantic acceptance is owned by `math/specification/correspondence.toml`.
